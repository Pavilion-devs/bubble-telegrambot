import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN, SUPPORTED_CHAINS, WELCOME_MESSAGE, HELP_MESSAGE
from utils.bubblemaps import BubblemapsAPI
from utils.screenshot import ScreenshotGenerator
from utils.token_metrics import TokenMetrics
import telegram

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize API clients
bubblemaps = BubblemapsAPI()
screenshot_gen = ScreenshotGenerator()
token_metrics = TokenMetrics()

# Define conversation states
ADDRESS_INPUT = 1
CHAIN_SELECTION = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    try:
        keyboard = [
            [InlineKeyboardButton("🔍 Analyze Token", callback_data="start_analysis")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        chains_list = ", ".join(SUPPORTED_CHAINS.keys())
        
        # Add retry logic for network operations
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                await update.message.reply_text(
                    WELCOME_MESSAGE.format(chains=chains_list),
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                break
            except telegram.error.NetworkError as e:
                if attempt == max_retries - 1:  # Last attempt
                    await update.message.reply_text(
                        "😔 Network connection issue detected. Please try:\n\n"
                        "1. Check your internet connection\n"
                        "2. Wait a few moments and try again\n"
                        "3. If the problem persists, try /start again\n\n"
                        "Error details: Network connectivity issue"
                    )
                    logger.error(f"Network error in start command: {e}")
                    return
                await asyncio.sleep(retry_delay * (attempt + 1))
            except telegram.error.TelegramError as e:
                await update.message.reply_text(
                    "😔 Sorry, I encountered an error. Please try again in a moment.\n"
                    "If the problem persists, use /start to restart our conversation."
                )
                logger.error(f"Telegram error in start command: {e}")
                return
    except Exception as e:
        logger.error(f"Unexpected error in start command: {e}")
        try:
            await update.message.reply_text(
                "😔 Something went wrong. Please try:\n\n"
                "1. Wait a few moments\n"
                "2. Use /start to try again\n"
                "3. If the problem continues, please try later"
            )
        except:
            pass  # If we can't even send the error message, just log it

async def start_token_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the token analysis flow"""
    try:
        query = update.callback_query
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                await query.answer()
                await query.edit_message_text(
                    "Please enter the token address you want to analyze:",
                    parse_mode='Markdown'
                )
                break
            except telegram.error.NetworkError as e:
                if attempt == max_retries - 1:  # Last attempt
                    await query.message.reply_text(
                        "😔 Network connection issue detected. Please try:\n\n"
                        "1. Check your internet connection\n"
                        "2. Wait a few moments and click the button again\n"
                        "3. If the problem persists, use /start to restart\n\n"
                        "Error details: Network connectivity issue"
                    )
                    logger.error(f"Network error in start_token_analysis: {e}")
                    return ConversationHandler.END
                await asyncio.sleep(retry_delay * (attempt + 1))
            except telegram.error.TelegramError as e:
                await query.message.reply_text(
                    "😔 Sorry, I encountered an error. Please try again in a moment.\n"
                    "If the problem persists, use /start to restart our conversation."
                )
                logger.error(f"Telegram error in start_token_analysis: {e}")
                return ConversationHandler.END
                
        return ADDRESS_INPUT
        
    except Exception as e:
        logger.error(f"Unexpected error in start_token_analysis: {e}")
        try:
            await query.message.reply_text(
                "😔 Something went wrong. Please try:\n\n"
                "1. Wait a few moments\n"
                "2. Use /start to try again\n"
                "3. If the problem continues, please try later"
            )
        except:
            pass  # If we can't even send the error message, just log it
        return ConversationHandler.END

async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the token address input and show chain selection"""
    address = update.message.text.strip()
    
    # Basic address validation
    if not re.match(r'^(0x)?[0-9a-fA-F]{40}$', address) and not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        await update.message.reply_text(
            "❌ Invalid token address format. Please enter a valid token address.",
            parse_mode='Markdown'
        )
        return ADDRESS_INPUT
    
    # Store the address in context
    context.user_data['token_address'] = address
    
    # Create keyboard with supported chains
    keyboard = []
    row = []
    for i, chain in enumerate(SUPPORTED_CHAINS.keys(), 1):
        row.append(InlineKeyboardButton(chain, callback_data=f"chain_{chain}"))
        if i % 3 == 0:  # 3 buttons per row
            keyboard.append(row)
            row = []
    if row:  # Add any remaining buttons
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Select the blockchain network:",
        reply_markup=reply_markup
    )
    return CHAIN_SELECTION

async def handle_chain_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the chain selection and start analysis"""
    query = update.callback_query
    await query.answer()
    
    chain = query.data.replace("chain_", "")
    address = context.user_data.get('token_address')
    
    if not address:
        await query.edit_message_text(
            "❌ Error: Token address not found. Please start over.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Clear the stored address
    del context.user_data['token_address']
    
    # Start the analysis
    message = await query.message.reply_text("🔍 Analyzing token... Please wait.")
    
    try:
        # Check if the bubble map is available
        map_available = await bubblemaps.check_map_availability(address, chain)
        
        # Gather data asynchronously
        metrics_task = token_metrics.get_combined_metrics(address, chain)
        score_task = bubblemaps.get_decentralization_score(address, chain)
        holder_task = bubblemaps.get_holder_data(address, chain)
        
        metrics, score, holder_data = await asyncio.gather(
            metrics_task, score_task, holder_task
        )

        # Generate bubble map screenshot
        bubble_map_url = bubblemaps.get_bubble_map_url(address, chain)
        
        # Use iframe URL if available for better screenshots
        iframe_url = None
        if map_available:
            iframe_url = bubblemaps.get_iframe_url(address, chain)
        
        try:
            screenshot = await screenshot_gen.capture_bubble_map(bubble_map_url, iframe_url)
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            screenshot = None

        # Prepare response message
        response = f"📊 *Token Analysis*\n\n"
        
        # Add metrics
        if metrics and metrics.get("price"):
            response += f"💰 Price: ${metrics['price']:,.6f}\n"
        if metrics and metrics.get("market_cap"):
            response += f"📈 Market Cap: ${metrics['market_cap']:,.2f}\n"
        if metrics and metrics.get("volume_24h"):
            response += f"🔄 24h Volume: ${metrics['volume_24h']:,.2f}\n"
        if metrics and metrics.get("price_change_24h"):
            change = metrics["price_change_24h"]
            emoji = "🟢" if change > 0 else "🔴"
            response += f"{emoji} 24h Change: {change:+.2f}%\n"

        # Add decentralization score
        if score is not None:
            response += f"\n🎯 Decentralization Score: {score:.2f}/100\n"
            
            # Add supply distribution
            if holder_data and holder_data.get("supply_distribution"):
                cex_percent = holder_data["supply_distribution"]["in_cexs"]
                contract_percent = holder_data["supply_distribution"]["in_contracts"]
                response += f"\n📊 Supply Distribution:\n"
                response += f"• In CEXs: {cex_percent:.2f}%\n"
                response += f"• In Contracts: {contract_percent:.2f}%\n"

        # Check if we have meaningful data
        has_data = (score is not None) or (metrics and metrics.get("price") is not None) or (holder_data and holder_data.get("top_holders"))
        
        if not has_data:
            await message.edit_text(
                f"❌ No data found for this token on {chain}.\n\n"
                f"This might be because:\n"
                f"• The token is not tracked by Bubblemaps yet\n"
                f"• The address or chain might be incorrect\n\n"
                f"Try another token or check the address."
            )
            return ConversationHandler.END

        # Add holder information
        if holder_data and holder_data.get("top_holders"):
            response += f"\n👥 Top Holders:\n"
            for i, holder in enumerate(holder_data["top_holders"][:5], 1):
                name = holder["name"] if holder["name"] != "Unknown" else holder["address"][:8] + "..." + holder["address"][-6:]
                contract_emoji = "📜" if holder["is_contract"] else "👤"
                response += f"{i}. {contract_emoji} {name}: {holder['percentage']:.2f}%\n"

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{address}_{chain}"),
                InlineKeyboardButton("📊 Show Score Only", callback_data=f"score_{address}_{chain}")
            ],
            [
                InlineKeyboardButton("🔗 View on Bubblemaps", url=bubble_map_url)
            ]
        ]
        
        # Add iframe button if available
        if map_available and iframe_url:
            keyboard.append([
                InlineKeyboardButton("🖼️ View Interactive Map", url=iframe_url)
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send screenshot if available
        if screenshot:
            try:
                await query.message.reply_photo(
                    photo=screenshot,
                    caption=response,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                await message.delete()
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                # If photo sending fails, fall back to text-only response
                await query.message.reply_text(
                    response + "\n\n*Note: Could not load visualization.*",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await query.message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await message.delete()

    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        await message.edit_text(
            "❌ Sorry, there was an error analyzing the token. Please try again later."
        )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    await update.message.reply_text(
        "Token analysis cancelled. You can start a new analysis anytime!"
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued."""
    # Provide an inline Analyze Token button on the help message
    keyboard = [
        [InlineKeyboardButton("🔍 Analyze Token", callback_data="start_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help button callback"""
    query = update.callback_query
    await query.answer()
    # Provide an inline Analyze Token button on the help screen
    keyboard = [
        [InlineKeyboardButton("🔍 Analyze Token", callback_data="start_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        HELP_MESSAGE,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def extract_token_chain(args):
    """Extract token address and chain from command arguments."""
    if not args:
        return None, None
    
    # Check for "on" keyword to separate address and chain
    full_text = " ".join(args)
    pattern = r'(0x[a-fA-F0-9]+|[a-zA-Z0-9]+)\s+(?:on|ON)\s+([a-zA-Z]+)'
    match = re.search(pattern, full_text)
    
    if match:
        address = match.group(1)
        chain = match.group(2).upper()
        return address, chain
    
    # If only one argument, assume it's the address and chain is ETH
    if len(args) == 1:
        return args[0], "ETH"
    
    # If 2+ arguments, assume the first is address, last is chain
    return args[0], args[-1].upper()

async def analyze_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze a token and send the results."""
    # Normalize arguments: remove empty or whitespace-only args
    clean_args = [arg for arg in context.args if arg and arg.strip()]
    # If no meaningful arguments, start interactive analysis flow
    if not clean_args:
        keyboard = [[InlineKeyboardButton("🔍 Analyze Token", callback_data="start_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please enter the token address you want to analyze:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADDRESS_INPUT
    try:
        # Extract address and chain from arguments
        address, chain = await extract_token_chain(clean_args)
        
        if not address or not chain:
            await update.message.reply_text(
                "🤔 I couldn't understand that format.\n\n"
                "Please use: `/analyze <address> on <chain>`\n"
                "Example: `/analyze 0xABC123 on ETH`\n\n"
                "Type /help for more examples.",
                parse_mode='Markdown'
            )
            return

        # Validate chain
        if chain not in SUPPORTED_CHAINS:
            chains_list = ", ".join(SUPPORTED_CHAINS.keys())
            await update.message.reply_text(
                f"❌ Unsupported chain: `{chain}`\n\n"
                f"Supported chains: {chains_list}",
                parse_mode='Markdown'
            )
            return

        # Send initial message
        message = await update.message.reply_text("🔍 Analyzing token... Please wait.")

        try:
            # Check if the bubble map is available
            map_available = await bubblemaps.check_map_availability(address, chain)
            
            # Gather data asynchronously
            metrics_task = token_metrics.get_combined_metrics(address, chain)
            score_task = bubblemaps.get_decentralization_score(address, chain)
            holder_task = bubblemaps.get_holder_data(address, chain)
            
            metrics, score, holder_data = await asyncio.gather(
                metrics_task, score_task, holder_task
            )
        except Exception as e:
            logger.error(f"API fetch error: {e}")
            await message.edit_text(
                f"❌ Error fetching data: {str(e)}\n\n"
                f"This might be because:\n"
                f"• The token doesn't exist on {chain}\n"
                f"• The address format is incorrect\n"
                f"• The API is currently unavailable\n\n"
                f"Please try again later or try a different token."
            )
            return

        # Generate bubble map screenshot
        bubble_map_url = bubblemaps.get_bubble_map_url(address, chain)
        
        # Use iframe URL if available for better screenshots
        iframe_url = None
        if map_available:
            iframe_url = bubblemaps.get_iframe_url(address, chain)
            print(f"Using iframe URL for screenshot: {iframe_url}")
        
        try:
            screenshot = await screenshot_gen.capture_bubble_map(bubble_map_url, iframe_url)
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            screenshot = None  # We'll continue without a screenshot

        # Prepare response message
        response = f"📊 *Token Analysis*\n\n"
        
        # Add metrics
        if metrics["price"]:
            response += f"💰 Price: ${metrics['price']:,.6f}\n"
        if metrics["market_cap"]:
            response += f"📈 Market Cap: ${metrics['market_cap']:,.2f}\n"
        if metrics["volume_24h"]:
            response += f"🔄 24h Volume: ${metrics['volume_24h']:,.2f}\n"
        if metrics["price_change_24h"]:
            change = metrics["price_change_24h"]
            emoji = "🟢" if change > 0 else "🔴"
            response += f"{emoji} 24h Change: {change:+.2f}%\n"

        # Add decentralization score
        if score is not None:
            response += f"\n🎯 Decentralization Score: {score:.2f}/100\n"
            
            # Add supply distribution
            if holder_data["supply_distribution"]:
                cex_percent = holder_data["supply_distribution"]["in_cexs"]
                contract_percent = holder_data["supply_distribution"]["in_contracts"]
                response += f"\n📊 Supply Distribution:\n"
                response += f"• In CEXs: {cex_percent:.2f}%\n"
                response += f"• In Contracts: {contract_percent:.2f}%\n"

        # Check if we have meaningful data
        has_data = (score is not None) or (metrics["price"] is not None) or holder_data["top_holders"]
        
        if not has_data:
            await message.edit_text(
                f"❌ No data found for this token on {chain}.\n\n"
                f"This might be because:\n"
                f"• The token is not tracked by Bubblemaps yet\n"
                f"• The address or chain might be incorrect\n\n"
                f"Try another token or check the address."
            )
            return

        # Add holder information
        if holder_data["top_holders"]:
            response += f"\n👥 Top Holders:\n"
            for i, holder in enumerate(holder_data["top_holders"][:5], 1):
                name = holder["name"] if holder["name"] != "Unknown" else holder["address"][:8] + "..." + holder["address"][-6:]
                contract_emoji = "📜" if holder["is_contract"] else "👤"
                response += f"{i}. {contract_emoji} {name}: {holder['percentage']:.2f}%\n"

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{address}_{chain}"),
                InlineKeyboardButton("📊 Show Score Only", callback_data=f"score_{address}_{chain}")
            ],
            [
                InlineKeyboardButton("🔗 View on Bubblemaps", url=bubble_map_url)
            ]
        ]
        
        # Add iframe button if available
        if map_available and iframe_url:
            keyboard.append([
                InlineKeyboardButton("🖼️ View Interactive Map", url=iframe_url)
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send screenshot if available
        if screenshot:
            try:
                await update.message.reply_photo(
                    photo=screenshot,
                    caption=response,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                # If photo sending fails, fall back to text-only response
                await update.message.reply_text(
                    response + "\n\n*Note: Could not load visualization.*",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        # Delete the "analyzing" message
        await message.delete()

    except Exception as e:
        logger.error(f"Error in analyze_token: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error analyzing the token. Please try again later."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    try:
        action, address, chain = query.data.split('_')
        
        if action == "refresh":
            # Send initial "analyzing" message
            message = await query.message.reply_text("🔍 Analyzing token... Please wait.")
            
            try:
                # Check if the bubble map is available
                map_available = await bubblemaps.check_map_availability(address, chain)
                
                # Gather data asynchronously
                metrics_task = token_metrics.get_combined_metrics(address, chain)
                score_task = bubblemaps.get_decentralization_score(address, chain)
                holder_task = bubblemaps.get_holder_data(address, chain)
                
                metrics, score, holder_data = await asyncio.gather(
                    metrics_task, score_task, holder_task
                )

                # Generate bubble map screenshot
                bubble_map_url = bubblemaps.get_bubble_map_url(address, chain)
                
                # Use iframe URL if available for better screenshots
                iframe_url = None
                if map_available:
                    iframe_url = bubblemaps.get_iframe_url(address, chain)
                
                try:
                    screenshot = await screenshot_gen.capture_bubble_map(bubble_map_url, iframe_url)
                except Exception as e:
                    logger.error(f"Screenshot error: {e}")
                    screenshot = None

                # Prepare response message
                response = f"📊 *Token Analysis*\n\n"
                
                # Add metrics
                if metrics and metrics.get("price"):
                    response += f"💰 Price: ${metrics['price']:,.6f}\n"
                if metrics and metrics.get("market_cap"):
                    response += f"📈 Market Cap: ${metrics['market_cap']:,.2f}\n"
                if metrics and metrics.get("volume_24h"):
                    response += f"🔄 24h Volume: ${metrics['volume_24h']:,.2f}\n"
                if metrics and metrics.get("price_change_24h"):
                    change = metrics["price_change_24h"]
                    emoji = "🟢" if change > 0 else "🔴"
                    response += f"{emoji} 24h Change: {change:+.2f}%\n"

                # Add decentralization score
                if score is not None:
                    response += f"\n🎯 Decentralization Score: {score:.2f}/100\n"
                    
                    # Add supply distribution
                    if holder_data and holder_data.get("supply_distribution"):
                        cex_percent = holder_data["supply_distribution"]["in_cexs"]
                        contract_percent = holder_data["supply_distribution"]["in_contracts"]
                        response += f"\n📊 Supply Distribution:\n"
                        response += f"• In CEXs: {cex_percent:.2f}%\n"
                        response += f"• In Contracts: {contract_percent:.2f}%\n"

                # Check if we have meaningful data
                has_data = (score is not None) or (metrics and metrics.get("price") is not None) or (holder_data and holder_data.get("top_holders"))
                
                if not has_data:
                    await message.edit_text(
                        f"❌ No data found for this token on {chain}.\n\n"
                        f"This might be because:\n"
                        f"• The token is not tracked by Bubblemaps yet\n"
                        f"• The address or chain might be incorrect\n\n"
                        f"Try another token or check the address."
                    )
                    return

                # Add holder information
                if holder_data and holder_data.get("top_holders"):
                    response += f"\n👥 Top Holders:\n"
                    for i, holder in enumerate(holder_data["top_holders"][:5], 1):
                        name = holder["name"] if holder["name"] != "Unknown" else holder["address"][:8] + "..." + holder["address"][-6:]
                        contract_emoji = "📜" if holder["is_contract"] else "👤"
                        response += f"{i}. {contract_emoji} {name}: {holder['percentage']:.2f}%\n"

                # Create inline keyboard
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{address}_{chain}"),
                        InlineKeyboardButton("📊 Show Score Only", callback_data=f"score_{address}_{chain}")
                    ],
                    [
                        InlineKeyboardButton("🔗 View on Bubblemaps", url=bubble_map_url)
                    ]
                ]
                
                # Add iframe button if available
                if map_available and iframe_url:
                    keyboard.append([
                        InlineKeyboardButton("🖼️ View Interactive Map", url=iframe_url)
                    ])
                    
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send screenshot if available
                if screenshot:
                    try:
                        await query.message.reply_photo(
                            photo=screenshot,
                            caption=response,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Error sending photo: {e}")
                        # If photo sending fails, fall back to text-only response
                        await query.message.reply_text(
                            response + "\n\n*Note: Could not load visualization.*",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                else:
                    await query.message.reply_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )

                # Delete the "analyzing" message
                await message.delete()

            except Exception as e:
                logger.error(f"Error in refresh: {e}")
                await message.edit_text(
                    "❌ Sorry, there was an error refreshing the token data. Please try again later."
                )

        elif action == "score":
            # Show only the decentralization score
            score = await bubblemaps.get_decentralization_score(address, chain)
            
            # Check if the message has text or photo
            has_photo = query.message.photo
            
            if score is not None:
                message_text = f"🎯 Decentralization Score: {score:.2f}/100"
                
                if has_photo:
                    # If it's a photo message, send a new message instead of editing
                    await query.message.reply_text(
                        message_text,
                        parse_mode='Markdown'
                    )
                else:
                    # If it's a text message, edit it
                    await query.edit_message_text(
                        message_text,
                        parse_mode='Markdown'
                    )
            else:
                message_text = "❌ Could not retrieve decentralization score."
                
                if has_photo:
                    # If it's a photo message, send a new message
                    await query.message.reply_text(
                        message_text,
                        parse_mode='Markdown'
                    )
                else:
                    # If it's a text message, edit it
                    await query.edit_message_text(
                        message_text,
                        parse_mode='Markdown'
                    )

    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        # Send a new message instead of trying to edit
        await query.message.reply_text(
            "❌ Sorry, there was an error processing your request.",
            parse_mode='Markdown'
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors globally"""
    logger.error("Exception while handling an update:", exc_info=context.error)

    try:
        # Get the error message
        error_msg = str(context.error)
        
        # Extract the chat id from the update object
        if update and (
            (isinstance(update, Update) and update.effective_chat) or 
            (hasattr(update, 'callback_query') and update.callback_query.message.chat)
        ):
            chat = update.effective_chat if isinstance(update, Update) else update.callback_query.message.chat
            
            if isinstance(context.error, telegram.error.NetworkError):
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="😔 Network connection issue detected. Please try:\n\n"
                         "1. Check your internet connection\n"
                         "2. Wait a few moments and try again\n"
                         "3. If the problem persists, use /start to restart\n\n"
                         "Error details: Network connectivity issue"
                )
            elif isinstance(context.error, telegram.error.TelegramError):
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="😔 Sorry, I encountered a Telegram API error. Please try again in a moment.\n"
                         "If the problem persists, use /start to restart our conversation."
                )
            else:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="😔 An unexpected error occurred. Please try:\n\n"
                         "1. Wait a few moments\n"
                         "2. Use /start to try again\n"
                         "3. If the problem continues, please try later"
                )
    except:
        logger.error("Error in error handler", exc_info=True)

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Set up error handler
    application.add_error_handler(error_handler)

    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_token_analysis, pattern="^start_analysis$"),
            CallbackQueryHandler(help_callback, pattern="^help$"),
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            CommandHandler("analyze", analyze_token)
        ],
        states={
            ADDRESS_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_input),
                CallbackQueryHandler(start_token_analysis, pattern="^start_analysis$")  # Allow analyze button during address input
            ],
            CHAIN_SELECTION: [
                CallbackQueryHandler(handle_chain_selection, pattern="^chain_"),
                CallbackQueryHandler(start_token_analysis, pattern="^start_analysis$")  # Allow analyze button during chain selection
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(help_callback, pattern="^help$"),
            CallbackQueryHandler(start_token_analysis, pattern="^start_analysis$")  # Allow analyze button in fallbacks
        ],
        per_message=False,
        name="token_analysis"
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))  # Handle other button callbacks

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 