# -*- coding: utf-8 -*-
#################################################################################
# Author      : Melkart O&B (melkart.io)
# Copyright(c): 2021 - Melkart O&B
# All Rights Reserved.
# gnjy-grjn-j473
#################################################################################

{
    'name': 'Bebepolis',
    'category': 'Point of Sale',
    'summary': 'Módulo customizado de Bebepolis',
    'description': """""",
    'author': 'Melkart O&B',
    'website': 'https://melkart.io',
    'version': '1.0.0',
    'depends': [
        'base', 'sale_management', 'account',
        'stock', 'website_sale', 'purchase',
        'point_of_sale', 'stock_barcode', 'maintenance',
        'sale_enterprise', 'purchase_enterprise', 'web_enterprise',
        'stock_enterprise', 'sale_shop',
        'prestashop_connector_gt'
    ],
    "data": [
        'views/pos_assets_common.xml',
        'views/pos_session.xml',
        'reports/report_cashcount.xml',
    ],
    'qweb': [
        'static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
