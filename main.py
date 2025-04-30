import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, SUPPORTED_CHAINS, WELCOME_MESSAGE, HELP_MESSAGE
from utils.bubblemaps import BubblemapsAPI
from utils.screenshot import ScreenshotGenerator
from utils.token_metrics import TokenMetrics

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    chains_list = ", ".join(SUPPORTED_CHAINS.keys())
    await update.message.reply_text(
        WELCOME_MESSAGE.format(chains=chains_list),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued."""
    await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

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
    try:
        # Extract address and chain from arguments
        address, chain = await extract_token_chain(context.args)
        
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
            # Re-analyze the token
            context.args = [address, "on", chain]
            await analyze_token(update, context)
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

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_token))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 