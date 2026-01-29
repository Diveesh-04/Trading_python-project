import argparse
import sys
from .market_orders import MarketOrder
from .limit_orders import LimitOrder
from .advanced.stop_limit_orders import StopLimitOrder
from .advanced.oco_orders import OCOOrder
from .advanced.twap_orders import TWAPOrder
from .advanced.grid_orders import GridOrder
from .logger import logger

def main():
    parser = argparse.ArgumentParser(description="Binance Futures Trading Bot")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Market order command
    market_parser = subparsers.add_parser('market', help='Place market order')
    market_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    market_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    market_parser.add_argument('quantity', help='Order quantity')
    
    # Limit order command
    limit_parser = subparsers.add_parser('limit', help='Place limit order')
    limit_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    limit_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    limit_parser.add_argument('quantity', help='Order quantity')
    limit_parser.add_argument('price', help='Limit price')
    
    # Stop-Limit order command
    stop_limit_parser = subparsers.add_parser('stop-limit', help='Place stop-limit order (triggers limit order when stop price is hit)')
    stop_limit_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    stop_limit_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    stop_limit_parser.add_argument('quantity', help='Order quantity')
    stop_limit_parser.add_argument('limit_price', help='Limit price (execution price)')
    stop_limit_parser.add_argument('stop_price', help='Stop price (trigger price)')
    
    # OCO order command
    oco_parser = subparsers.add_parser('oco', help='Place OCO order (take-profit and stop-loss simultaneously)')
    oco_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    oco_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    oco_parser.add_argument('quantity', help='Order quantity')
    oco_parser.add_argument('take_profit', help='Take-profit price')
    oco_parser.add_argument('stop_loss', help='Stop-loss price')
    
    # TWAP order command
    twap_parser = subparsers.add_parser('twap', help='Place TWAP order (split large orders into chunks over time)')
    twap_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    twap_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    twap_parser.add_argument('quantity', help='Total order quantity')
    twap_parser.add_argument('duration', type=int, help='Duration in minutes')
    twap_parser.add_argument('--slices', type=int, help='Number of slices (defaults to duration_minutes)')
    
    # Grid order command
    grid_parser = subparsers.add_parser('grid', help='Place grid order (automated buy-low/sell-high within price range)')
    grid_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    grid_parser.add_argument('lower_price', help='Lower bound of price range')
    grid_parser.add_argument('upper_price', help='Upper bound of price range')
    grid_parser.add_argument('levels', type=int, help='Number of grid levels')
    grid_parser.add_argument('quantity', help='Quantity per grid level')
    
    args = parser.parse_args()
    
    result = None
    
    if args.command == 'market':
        bot = MarketOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            quantity=args.quantity
        )
        
    elif args.command == 'limit':
        bot = LimitOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            quantity=args.quantity,
            price=args.price
        )
        
    elif args.command == 'stop-limit':
        bot = StopLimitOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            quantity=args.quantity,
            limit_price=args.limit_price,
            stop_price=args.stop_price
        )
        
    elif args.command == 'oco':
        bot = OCOOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            quantity=args.quantity,
            take_profit_price=args.take_profit,
            stop_loss_price=args.stop_loss
        )
        
    elif args.command == 'twap':
        bot = TWAPOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            total_quantity=args.quantity,
            duration_minutes=args.duration,
            num_slices=args.slices
        )
        
    elif args.command == 'grid':
        bot = GridOrder()
        result = bot.execute(
            symbol=args.symbol.upper(),
            lower_price=args.lower_price,
            upper_price=args.upper_price,
            grid_levels=args.levels,
            quantity_per_level=args.quantity
        )
        
    else:
        parser.print_help()
        sys.exit(1)
    
    # Display results based on order type
    if result and result.get("success"):
        print(f"✅ Order successful!")
        
        if args.command in ['market', 'limit', 'stop-limit']:
            print(f"   Order ID: {result.get('order_id')}")
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Side: {result.get('side')}")
            print(f"   Quantity: {result.get('quantity')}")
            if result.get('price'):
                print(f"   Price: {result.get('price')}")
            if result.get('limit_price'):
                print(f"   Limit Price: {result.get('limit_price')}")
            if result.get('stop_price'):
                print(f"   Stop Price: {result.get('stop_price')}")
        
        elif args.command == 'oco':
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Quantity: {result.get('quantity')}")
            tp = result.get('take_profit', {})
            sl = result.get('stop_loss', {})
            print(f"   Take-Profit Order ID: {tp.get('order_id')}")
            print(f"   Take-Profit Price: {tp.get('price')}")
            print(f"   Stop-Loss Order ID: {sl.get('order_id')}")
            print(f"   Stop-Loss Price: {sl.get('stop_price')}")
        
        elif args.command == 'twap':
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Side: {result.get('side')}")
            print(f"   Total Quantity: {result.get('total_quantity')}")
            print(f"   Executed Quantity: {result.get('executed_quantity')}")
            print(f"   Average Price: ${result.get('average_price', 0):.2f}")
            print(f"   Number of Slices: {result.get('num_slices')}")
            orders = result.get('orders', [])
            if orders:
                print(f"   Orders: {', '.join(str(o['order_id']) for o in orders)}")
        
        elif args.command == 'grid':
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Grid Levels: {result.get('grid_levels')}")
            print(f"   Price Range: ${result.get('price_range', {}).get('lower')} - ${result.get('price_range', {}).get('upper')}")
            print(f"   Quantity per Level: {result.get('quantity_per_level')}")
            print(f"   Current Price: ${result.get('current_price')}")
            print(f"   Orders Placed: {result.get('orders_placed')} ({result.get('buy_orders')} buy, {result.get('sell_orders')} sell)")
            orders = result.get('orders', [])
            if orders:
                print(f"   Order IDs: {', '.join(str(o['order_id']) for o in orders[:5])}{'...' if len(orders) > 5 else ''}")
    else:
        error_msg = result.get('error') if result else "Unknown error"
        print(f"❌ Order failed: {error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()