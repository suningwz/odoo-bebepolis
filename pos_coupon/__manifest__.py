{
    'name': 'Point of Sale COUPONS',
    'version': '13.0.1.',
    'category': 'Point of Sale',
    'summary': 'Point of Sale COUPONS',
    'author': 'Melkart OB',
    'website': "https://melkart.op",
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/coupon.xml',
        'views/coupon.xml',
        'templates/assets.xml',
    ],
    'qweb': [],
    'images': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}