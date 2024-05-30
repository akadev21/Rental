{
    'name': 'Rental Management',
    'version': '14.0',
    'sequence': -15,
    'summary': 'App for managing rentals',
    'category': 'Management',
    'author': 'Ouchari Ibrahim',
    'depends': ['base', 'product', 'stock', 'sale', 'web_timeline'],  # Added dependency on the base module
    'data': [
        'secrurity/ir.model.access.csv',
        'wizard/pickup_order_wizard.xml',
        'wizard/return_order_wizard.xml',
        'views/rental_order_view.xml',
        'views/product_view.xml',
        'views/rental_period_view.xml',
        'views/menu_item.xml',
        'views/rental_stock_view.xml',
        'views/rental_report_view.xml',

    ],
    'assets': {
        'web.assets_backend': ['rent/static/src/css/style.css']
    },
    'installable': True,
    'application': True
}
