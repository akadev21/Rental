{
    'name': 'Rental Management',
    'version': '14.0',
    'sequence': -15,
    'summary': 'App for managing rentals',
    'category': 'Management',
    'author': 'Ouchari Ibrahim',
    'depends': ['base', 'product','stock','sale'],  # Added dependency on the base module
    'data': [
        'secrurity/ir.model.access.csv',
        'views/rental_order_view.xml',
        'views/product_view.xml',
        'views/rental_period_view.xml',
        'views/menu_item.xml',

    ],
    'installable': True,
    'application': True
}
