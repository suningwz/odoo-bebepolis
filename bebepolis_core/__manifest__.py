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
    "data": [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
