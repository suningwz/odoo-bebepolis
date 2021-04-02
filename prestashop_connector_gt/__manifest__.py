# -*- coding: utf-8 -*-
##############################################################################
#    Globalteckz Pvt Ltd
##############################################################################

{
    "name" : "Prestashop Connector",
    "version" : "1.0",
    "depends" : ["sale_stock",'delivery','account','sale_shop','product_images_olbs'],
    "author" : "Globalteckz",
    'summary': 'Manage all your prestashop operations in Odoo Amazon Odoo Bridge(AOB) Amazon Odoo connector Odoo Amazon bridge Odoo amazon connector Connectors Odoo bridge Amazon to odoo Manage orders Manage products Import products Import customers Import orders Ebay to Odoo Odoo multi-channel bridge Multi channel connector Multi platform connector Multiple platforms bridge Connect Amazon with odoo Amazon bridge Flipkart Bridge Magento Odoo Bridge Odoo magento bridge Woocommerce odoo bridge Odoo woocommerce bridge Ebay odoo bridge Odoo ebay bridge Multi channel bridge Prestashop odoo bridge Odoo prestahop Akeneo bridge Marketplace bridge Multi marketplace connector Multiple marketplace platform  odoo shopify shopify connector shopify bridge shipstation connector shipstation integration shipstation bridge',
    'images': ['static/description/Banner.gif'],
    "license" : "Other proprietary",
    "price": "350.00",
    "currency": "EUR",
    "description": """Prestashop E-commerce management""",
    "website" : "https://www.globalteckz.com/shop/odoo-apps/odoo-prestashop-connector/",
    'live_test_url': 'https://www.globalteckz.com/shop/odoo-apps/odoo-prestashop-connector/',
    "category" : "Ecommerce",
    "data" : [
            'security/prestashop_security.xml',
            'security/ir.model.access.csv',
            'data/product_data.xml',
            'data/schedular_data.xml',
	        'data/sequence_data.xml',
            'wizard/create_shop_view.xml',

            'wizard/prestashop_connector_wizard_view.xml',
            'views/prestashop_language_view.xml',
            'views/res_partner_view.xml',
            'views/prestashop_view.xml',
            'views/stock_view.xml',
            'views/prestashop_category_view.xml',
            'views/product_view.xml',
            'views/cart_rules.xml',
	        'views/prestashop_logs_view.xml',
            'views/catalog_price_rule.xml',
            'views/sale_view.xml',
            # 'views/account_invoice_view.xml',
            'views/order_message_view.xml',
            'views/dashboard_view.xml',
            'views/import_order_workflow.xml',
            'views/sale_shop.xml',

	        'views/prestashop_menus.xml'
    ],
    "active": True,
    "installable": True,
}
 # 'wizard/upload_customer_view.xml',
            # 'wizard/upload_products_view.xml',
            # 'wizard/upload_sale_order_view.xml',
            # 'wizard/upload_category_view.xml',
            # 'wizard/upload_cart_rule_view.xml',
            # 'wizard/catalog_price.xml',
