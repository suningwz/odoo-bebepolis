# -*- coding: utf-8 -*-
#############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# import urllib2
import urllib.request,json
import requests
import base64
# import urllib.request
import json
import ast
import pytz
from odoo import api, fields, models, _
import socket
from datetime import timedelta, datetime, date, time
import time
from odoo import SUPERUSER_ID
#import mx.DateTime as dt
from odoo import netsvc
from odoo.tools.translate import _
from operator import itemgetter
from itertools import groupby
import json
import string, random
import binascii
import logging
import cgi
logger = logging.getLogger('__name__')

import xml.etree.ElementTree as ET
from odoo.addons.prestashop_connector_gt.prestapyt.prestapyt import PrestaShopWebServiceError as PrestaShopWebServiceError
from odoo.addons.prestashop_connector_gt.prestapyt.prestapyt import PrestaShopWebService as PrestaShopWebService
from odoo.addons.prestashop_connector_gt.prestapyt.prestapyt import PrestaShopWebServiceDict as PrestaShopWebServiceDict
import logging

logger = logging.getLogger('stock')
from odoo.exceptions import UserError
import html2text

# try:
#     from urllib.request import urlopen
# except ImportError:
#     from urllib2 import urlopen


class SaleShop(models.Model):
	_inherit = "sale.shop"

	code = fields.Char(srting='Code')
	name = fields.Char('Name')

	prestashop_shop = fields.Boolean(srting='Prestashop Shop')
	prestashop_instance_id = fields.Many2one('prestashop.instance',srting='Prestashop Instance',readonly=True)
	presta_id = fields.Char(string='shop Id')

	### Product Configuration
	product_import_condition = fields.Boolean(string="Create New Product if Product not in System while import order",default=True)
	route_ids = fields.Many2many('stock.location.route', 'shop_route_rel', 'shop_id', 'route_id', string='Routes')

	# Order Information
	company_id = fields.Many2one('res.company', srting='Company', required=False,
								 default=lambda s: s.env['res.company']._company_default_get('stock.warehouse'))
	prefix = fields.Char(string='Prefix')
	suffix = fields.Char(string='Suffix')
	shipment_fee_product_id = fields.Many2one('product.product', string="Shipment Fee",domain="[('type', '=', 'service')]")
	gift_wrapper_fee_product_id = fields.Many2one('product.product', string="Gift Wrapper Fee",domain="[('type', '=', 'service')]")
	sale_journal = fields.Many2one('account.journal')
	pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
	partner_id = fields.Many2one('res.partner', string='Customer')
	workflow_id = fields.Many2one('import.order.workflow', string="Order Workflow")

	# stock Configuration
	on_fly_update_stock = fields.Boolean(string="Update on Shop at time of Odoo Inventory Change",default=True)
	warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

	# Schedular Configuration
	auto_import_order = fields.Boolean(string="Auto Import Order", default=True)
	auto_import_products = fields.Boolean(string="Auto Import Products", default=True)
	auto_update_inventory = fields.Boolean(string="Auto Update Inventory", default=True)
	auto_update_order_status = fields.Boolean(string="Auto Update Order Status", default=True)
	auto_update_product_data = fields.Boolean(string="Auto Update Product data", default=True)
	auto_update_price = fields.Boolean(string="Auto Update Price", default=True)

	# Import last date
	last_prestashop_inventory_import_date = fields.Datetime(string='Last Inventory Import Time')
	last_prestashop_product_import_date = fields.Datetime(string='Last Product Import Time')
	last_presta_product_attrs_import_date = fields.Datetime(string='Last Product Attributes Import Time')
	last_presta_cart_rule_import_date = fields.Datetime(string='Last Cart Rule Import Time')
	last_presta_catalog_rule_import_date = fields.Datetime(string='Last Catalog Rule Import Time')
	last_prestashop_order_import_date = fields.Datetime(string='Last Order Import Time')
	last_prestashop_carrier_import_date = fields.Datetime(string='Last Carrier Import Time')
	last_prestashop_msg_import_date = fields.Datetime(string='Last Message Import Time')
	last_prestashop_customer_import_date = fields.Datetime(string='Last Customer Import Time')
	last_prestashop_category_import_date = fields.Datetime(string='Last Category Import Time')
	last_prestashop_customer_address_import_date = fields.Datetime(string='Last Customer Address Import Time')
	last_attr_id = fields.Char("Attribute Id")

	#Update last date
	prestashop_last_update_category_date = fields.Datetime(srting='Presta last update category date')
	prestashop_last_update_cart_rule_date = fields.Datetime(srting='Presta last update cart rule date')
	prestashop_last_update_catalog_rule_date = fields.Datetime(srting='Presta last update catalog rule date')
	prestashop_last_update_product_data_date = fields.Datetime(srting='Presta last update product data rule date')
	prestashop_last_update_order_status_date = fields.Datetime(srting='Presta last update order status date')

	#Export last date
	prestashop_last_export_product_data_date = fields.Datetime(string= 'Last Product Export Time')

	shop_physical_url = fields.Char(string="Physical URL", required=False, )

	#chron functions
	# import_prestashop_orders_scheduler
	# @api.multi
	# def import_product_scheduler(self, cron_mode=True):
	# 	instance_obj = self.env['magento.instance']
	# 	instance_id = instance_obj.search([])
	# 	instance_id.import_products()
	# 	return True

	# @api.multi
	# def import_prestashop_orders_scheduler(self, cron_mode=True):
	# 	instance_obj = self.env['sale.shop']
	# 	search_ids = self.search([])
	# 	search_ids.import_orders()
	# 	return True

	# import_prestashop_products_scheduler
	# @api.model
	def import_prestashop_products_scheduler(self, cron_mode=True):
		search_ids = self.search([('prestashop_shop', '=', True), ('auto_import_products', '=', True)])
		if search_ids:
			search_ids.sorted(reverse=True)
			search_ids.import_products()
		return True

	# update_prestashop_product_data_scheduler
	# @api.model
	def update_prestashop_product_data_scheduler(self, cron_mode=True):
		search_ids = self.search([('prestashop_shop', '=', True), ('auto_update_product_data', '=', True)])
		if search_ids:
			search_ids.sorted(reverse=True)
			search_ids.update_products()
		return True

	# update_prestashop_inventory_scheduler
	# @api.model
	def update_prestashop_inventory_scheduler(self, cron_mode=True):
		search_ids = self.search([('prestashop_shop', '=', True), ('auto_update_inventory', '=', True)])
		if search_ids:
			search_ids.sorted(reverse=True)
			search_ids.update_presta_product_inventory()
		return True

	# update_prestashop_order_status_scheduler
	# @api.model
	def update_prestashop_order_status_scheduler(self, cron_mode=True):
		search_ids = self.search([('prestashop_shop', '=', True), ('auto_update_order_status', '=', True)])
		if search_ids:
			search_ids.sorted(reverse=True)
			search_ids.update_order_status()
		return True

	def presta_connect(self):
		if self.prestashop_instance_id:
			presta_instance=self.prestashop_instance_id
		else:
			context = dict(self._context or {})
			active_id = context.get('active_ids')
			presta_instance=self.env['prestashop.instance'].browse(active_id)
		location=presta_instance.location
		webservicekey=presta_instance.webservice_key
#         try:
		prestashop = PrestaShopWebService(location,webservicekey)
#         except e:
			#PrestaShopWebServiceError
#             print(str(e))
		return prestashop


	# @api.one
	def get_value_data(self, value):
		if isinstance(value, dict):
			return value.get('value')
		else:
			return value


	# @api.one
	def create_attr(self, attr_val, prestashop):
		print ("create_attrrrrrrrrrrrrr",attr_val)
		try:
			prod_att_obj = self.env['product.attribute']
			prod_attr_vals_obj = self.env['product.attribute.value']
			att_id = False

			attribute_value  = {
							'name':self.get_value_data(self.get_value(attr_val.get('name').get('language'))),
							'presta_id' : self.get_value_data(attr_val.get('id'))
			}
			attrs_ids = prod_att_obj.search([('presta_id','=', self.get_value_data(attr_val.get('id')))])
			if not attrs_ids:
				att_id = prod_att_obj.create(attribute_value)
			else:
				att_id = attrs_ids[0]
				attrs_ids.write(attribute_value)
			self.env.cr.execute("select attr_id from attr_shop_rel where attr_id = %s and shop_id = %s" % (att_id.id, self.id))
			attr_data = self.env.cr.fetchone()

			if attr_data == None:
				self.env.cr.execute("insert into attr_shop_rel values(%s,%s)" % (att_id.id, self.id))

			if attr_val.get('associations').get('product_option_values').get('product_option_value'):
				attributes = attr_val.get('associations').get('product_option_values').get('product_option_value')
				if isinstance(attributes, list):
							attributes = attributes
				else:
					attributes = [attributes]
				for attrs in attributes:
					product_options = prestashop.get('product_option_values', self.get_value_data(attrs.get('id')))
					product_options =  product_options.get('product_option_value')
					attrs_op_values = {
						'attribute_id': self.get_value_data(att_id.id),
						'presta_id': self.get_value_data(product_options.get('id')),
						"name": self.get_value_data(self.get_value(product_options.get('name').get('language'))),
					}
					attrs_ids = prod_attr_vals_obj.search([('presta_id', '=', self.get_value_data(product_options.get('id'))), ('attribute_id', '=', att_id.id)])
					if not attrs_ids:
						v_id = prod_attr_vals_obj.create(attrs_op_values)
						self.env.cr.commit()
						logger.info('Value ===> %s', v_id.name)
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id =  self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': "New error",'log_id':log_id,'prestashop_id':att_id.id})
			else:
				log_id_obj = self.env['prestashop.log'].create({'all_operations':'import_attributes','error_lines': [(0,0, {'log_description': 'atrs error','prestashop_id':att_id.id})]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return True

	# @api.multi
	def import_product_attributes(self):
		print ("import_product_attributeseeeeeeee")

		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location, shop.prestashop_instance_id.webservice_key or None)
			ctx = {'log_id': False}
			# try:
			last_import_attrs = shop.last_presta_product_attrs_import_date
			if last_import_attrs:
				last_imported_attrs = last_import_attrs.date()
				product_options = prestashop.get('product_options',options={'filter[date_upd]':last_imported_attrs,'date':'1'})
			else:
				product_options = prestashop.get('product_options')
				if product_options.get('product_options') and product_options.get('product_options').get('product_option'):
					attributes = product_options.get('product_options').get('product_option')
					if isinstance(attributes, list):
						attributes = attributes
					else:
						attributes = [attributes]
					for attrs in attributes:
						data = self.get_value_data(attrs.get('attrs').get('id'))
						if data:
							vals = prestashop.get('product_options',data).get('product_option')
							# self.with_context(ctx).create_attr(vals, prestashop)
							shop.create_attr(vals, prestashop)
				shop.write({'last_presta_product_attrs_import_date': datetime.today()})
		return True


	# @api.one
	def get_categ_parent(self, prestashop, category):
		print ("=====get_categ_parent=======")
		# print "inside get_categ_parent===>",category
		prod_category_obj = self.env['prestashop.category']
		vals = {
			'presta_id': self.get_value_data(self.get_value_data(category.get('category').get('id'))),
			'name': self.get_value_data(self.get_value(category.get('category').get('name').get('language'))),
		}
		#
		category_check = prod_category_obj.search([('presta_id', '=',self.get_value_data(category.get('category').get('id_parent')))])

		if not category_check:
			print("ategory.get('category')===",category.get('category'))
			if category.get('category').get('id_parent').get('value') == 0:
				vals.update({'parent_id': False})
			else:
				categ = prestashop.get('categories', self.get_value_data(category.get('category').get('id_parent')))
				parent_id = self.get_categ_parent(prestashop, categ)
				# if parent_id:
				#     self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
				#         parent_id.id, self.id))
				#     categ_data = self.env.cr.fetchone()
				#     if categ_data == None:
				#         self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_id.id, self.id))

				vals.update({'parent_id': parent_id[0].id})
			parent_id = prod_category_obj.create(vals)
			logger.info('Created Category ===> %s'%(parent_id.id))
			# if parent_id:
			#     self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
			#         parent_id.id, self.id))
			#     categ_data = self.env.cr.fetchone()
			#     if categ_data == None:
			#         self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_id.id, self.id))
			return parent_id
		else:
			parent_id = prod_category_obj.create(vals)
			# if parent_id:
				# # print "==inside category_shop query loop second===========>"
				# self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
				#     parent_id.id, self.id))
				# categ_data = self.env.cr.fetchone()
				# # print "categ_data if part second=============================>", categ_data
				# if categ_data == None:
				#     self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_id.id, self.id))
			return parent_id


	# @api.one
	def create_presta_category(self, prestashop, category):
		print("====create_presta_category====>",category)
		prod_category_obj = self.env['prestashop.category']
		category_check = prod_category_obj.search([('presta_id', '=', self.get_value_data(category.get('category').get('id')))])
		try:
			if not category_check:
				vals = {'presta_id': self.get_value_data(category.get('category').get('id'))[0],
						'name': self.get_value_data(self.get_value(category.get('category').get('name').get('language'))),}

				parent_category_check = prod_category_obj.search([('presta_id', '=', self.get_value_data(category.get('category').get('id_parent')))])

				if not parent_category_check:
					logger.info('CATTTTTTTTTTTTTTT===> %s'%(category.get('category').get('id_parent')))
					if self.get_value_data(category.get('category').get('id_parent'))[0] != '0':

						valsss = prestashop.get('categories', self.get_value_data(category.get('category').get('id_parent')))
						parent_id = self.get_categ_parent(prestashop, valsss)[0].id
					else:
						parent_id = False
					if parent_id:
						self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
							parent_id, self.id))
						categ_data = self.env.cr.fetchone()
						if categ_data == None:
							self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_id, self.id))
					vals.update({'parent_id': parent_id})
				else:
					vals.update({'parent_id': parent_category_check[0].id})
					if parent_category_check[0].id:
						self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
							parent_category_check[0].id, self.id))
						categ_data = self.env.cr.fetchone()
						# print ("parent_id is 2=============================>", parent_category_check[0].id)
						if categ_data == None:
							self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_category_check[0].id, self.id))

				cat_id= prod_category_obj.create(vals)
				logger.info('Created Category ===> %s'%(cat_id.id))
				self.env.cr.commit()

				if cat_id:
					self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
						cat_id.id, self.id))
					categ_data = self.env.cr.fetchone()
					if categ_data == None:
						self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (cat_id.id, self.id))
				return cat_id
			else:
				vals = {
					'presta_id': self.get_value_data(category.get('category').get('id'))[0],
					'name': self.get_value_data(self.get_value(category.get('category').get('name').get('language'))),
				}
				parent_category_check = prod_category_obj.search([('presta_id', '=', self.get_value_data(category.get('category').get('id_parent')))])

				if not parent_category_check:
					if category.get('category').get('id_parent') != '0':
						valsss = prestashop.get('categories', self.get_value_data(category.get('category').get('id_parent')))
						parent_id = self.get_categ_parent(prestashop, valsss)[0].id

					else:
						parent_id = False
					vals.update({'parent_id': parent_id})
				else:
					vals.update({'parent_id': parent_category_check[0].id})
					parent_id = parent_category_check[0].id

				if parent_id:
					self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
						parent_id, self.id))
					categ_data = self.env.cr.fetchone()
					if categ_data == None:
						self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (parent_id, self.id))
				category_check[0].write(vals)

				if category_check[0]:
					self.env.cr.execute("select categ_id from presta_categ_shop_rel where categ_id = %s and shop_id = %s" % (
						category_check[0].id, self.id))
					categ_data = self.env.cr.fetchone()

					if categ_data == None:
						self.env.cr.execute("insert into presta_categ_shop_rel values(%s,%s)" % (category_check[0].id, self.id))

				return category_check[0]
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id =  self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create({'all_operations':'import_categories','error_lines': [(0,0, {'log_description': str(e),})]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return True

	# @api.multi
	def import_categories(self):
		print("====import_categories====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			ctx = {}
			last_import_category = shop.last_prestashop_category_import_date
			if last_import_category:
				last_imported_category = last_import_category.date()
				categ = prestashop.get('categories',options={'filter[date_upd]':last_imported_category,'date':'1'})
			else:
				categ = prestashop.get('categories')
				if categ.get('categories') and categ.get('categories').get('category'):
					categs = categ.get('categories').get('category')

					if isinstance(categs, list):
						categs = categs
					else:
						categs = [categs]
					for attrs in categs:
						data = attrs.get('attrs').get('id')
						if data:
							vals = prestashop.get('categories', data)
							shop.with_context(ctx).create_presta_category(prestashop, vals)
			shop.write({'last_prestashop_category_import_date':datetime.now()})
		return True


	# @api.one
	def create_customer(self, customer_detail, prestashop):
		print("====create_customer====>",customer_detail)

		res_partner_obj = self.env['res.partner']
		lan_obj= self.env['res.lang']
		cust_id=False
		dob = self.get_value_data(customer_detail.get('customer').get('birthday'))

		date_obj = False
		try:
			if dob and dob != '0000-00-00':
				date_obj = datetime.strptime(dob, '%Y-%m-%d')
			logger.info('===customer_detail========> %s',customer_detail.get('customer'))
			vals = {
				'presta_id': self.get_value_data(customer_detail.get('customer').get('id')),
				'name': self.get_value_data(customer_detail.get('customer').get('firstname')) + ' ' + self.get_value_data(customer_detail.get('customer').get(
					'lastname')) or ' ',
				'comment':self.get_value_data(customer_detail.get('customer').get('note')),
				'lang':self.get_value_data(customer_detail.get('customer').get('id_lang')),
				'customer_rank': True,
				'supplier_rank': False,
				'email': self.get_value_data(customer_detail.get('customer').get('email')),
				'website': self.get_value_data(customer_detail.get('customer').get('website')),
				'date_of_birth': date_obj and date_obj.date() or False,
			}
			logger.info('======vals of customer ===> %s',vals)

			if self.get_value_data(customer_detail.get('customer').get('id_lang')):
				lang_values = prestashop.get('languages',self.get_value_data(customer_detail.get('customer').get('id_lang')))
				lang = self.get_value_data(lang_values.get('language').get('language_code')).split('-')
				if len(lang) > 1:
					lan = lang[0] + '_' + lang[1].upper()
				else:
					lan = lang[0]
				lang_id = self.env['res.lang'].search([])
				cust_lang_ids = lan_obj.search([('code', '=', lang_id[0].code)])
				if cust_lang_ids:
					lang_id = cust_lang_ids[0]
					vals.update({
						'lang': lang_id.code
					})
				else:

					language_wiz_id = self.env['base.language.install'].create({
						'lang': 'en_Us',
					})
					language_wiz_id.lang_install()
					lang_ids = lan_obj.search([('code', '=', lan)])
					if lang_ids:
						vals.update({
							'lang': lang_ids[0].code
						})
			if self.get_value_data(customer_detail.get('customer').get('passwd')):
				customer_ids = res_partner_obj.search([('presta_id', '=', self.get_value_data(customer_detail.get('customer').get('id'))[0]),('customer_rank', '=', True),('supplier_rank', '=', False),('manufacturer', '=', False)])
				if not customer_ids:
					cust_id = res_partner_obj.create(vals)
					logger.info('Created Customer 1111===> %s'%(cust_id.id))
				else:
					cust_id = customer_ids[0]
					customer_ids.write(vals)
				if cust_id:
					self.env.cr.execute("select cust_id from customer_shop_rel where cust_id = %s and shop_id = %s" % (cust_id.id, self.id))
					cust_data = self.env.cr.fetchone()

				if cust_data== None:
					self.env.cr.execute("insert into customer_shop_rel values(%s,%s)" % (cust_id.id, self.id))
				self.env.cr.commit()
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_customers', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return cust_id


	# @api.multi
	def import_customers(self):
		print("====import_customers====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			ctx={}
			last_import_customer = shop.last_prestashop_customer_import_date
			if last_import_customer:
				last_imported_customer = last_import_customer.date()
				customers_data = prestashop.get('customers',options={'filter[date_upd]':last_imported_customer,'date':'1'})
			else:
				customers_data = prestashop.get('customers')
				if customers_data.get('customers') and customers_data.get('customers').get('customer'):
					customers = customers_data.get('customers').get('customer')
					if isinstance(customers, list):
						customers = customers
					else:
						customers = [customers]
					for cust in customers:

						customer_id = self.get_value_data(cust.get('attrs').get('id'))
						if customer_id:
							customer_detail = prestashop.get('customers', customer_id)
							self.with_context(ctx).create_customer(customer_detail, prestashop)
			shop.write({'last_prestashop_customer_import_date':datetime.today()})
			self.env.cr.commit()
		return  True


	# @api.one
	def create_presta_supplier(self, supplier_detail):
		print("====create_presta_supplier====>",supplier_detail)

		res_partner_obj = self.env['res.partner']
		try:
			vals = {
				'presta_id': self.get_value_data(supplier_detail.get('supplier').get('id')),
				'name': self.get_value_data(supplier_detail.get('supplier').get('name')),
				'supplier_rank': True,
				'customer_rank': False,
				'manufacturer': False,
			}
			logger.info('===vals======> %s',vals)

			supp_ids = res_partner_obj.search([('presta_id', '=', self.get_value_data(supplier_detail.get('supplier').get('id'))), ('supplier_rank', '=', True),('customer_rank', '=', False),('manufacturer','=',False)])
			if not supp_ids:
				supplier_id = res_partner_obj.create(vals)
				logger.info('Created Customer ===> %s' % (supplier_id.id))
			else:
				supplier_id =  supp_ids[0]

			if supplier_id:
				self.env.cr.execute(
					"select cust_id from customer_shop_rel where cust_id = %s and shop_id = %s" % (supplier_id.id, self.id))
				supplier_data = self.env.cr.fetchone()

			if supplier_data == None:
				self.env.cr.execute("insert into customer_shop_rel values(%s,%s)" % (supplier_id.id, self.id))
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_suppliers', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return True


	# @api.multi
	def import_suppliers(self):
		print("====import_supplier====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			supplier_data=prestashop.get('suppliers')
			if supplier_data.get('suppliers') and supplier_data.get('suppliers').get('supplier'):
				suppliers = supplier_data.get('suppliers').get('supplier')
				if isinstance(suppliers, list):
					suppliers = suppliers
				else:
					suppliers = [suppliers]
				for supplier in suppliers:
					supplier_id = self.get_value_data(supplier.get('attrs').get('id'))
					if supplier_id:
						supplier_detail = prestashop.get('suppliers', supplier_id)
						shop.create_presta_supplier(supplier_detail)
		return True


	# @api.one
	def create_presta_manufacturers(self, manufacturer_detail):
		print("====create_presta_manufacturers====>",manufacturer_detail)
		res_partner_obj = self.env['res.partner']
		try:
			vals = {
			'presta_id': self.get_value_data(manufacturer_detail.get('manufacturer').get('id')),
			'name': self.get_value_data(manufacturer_detail.get('manufacturer').get('name')),
			'manufacturer': True,
			'customer_rank': False,
			'supplier_rank': False,
			}
			manufact_ids = res_partner_obj.search([('presta_id', '=', self.get_value_data(manufacturer_detail.get('manufacturer').get('id'))),('manufacturer', '=', True)])
			if not manufact_ids:
				manufacturer_id = res_partner_obj.create(vals)
				self.env.cr.commit()
				logger.info('Created Customer ===> %s' % (manufacturer_id.id))
			else:
				manufacturer_id = manufact_ids[0]

			if manufacturer_id:
				self.env.cr.execute("select cust_id from customer_shop_rel where cust_id = %s and shop_id = %s" % (manufacturer_id.id, self.id))
				manufacturer_data = self.env.cr.fetchone()
			if manufacturer_data == None:
				self.env.cr.execute("insert into customer_shop_rel values(%s,%s)" % (manufacturer_id.id, self.id))
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_manufacturers', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return True


	# @api.multi
	def import_manufacturers(self):
		print("====import_manufacturers====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			manufacturer_data=prestashop.get('manufacturers')
			if manufacturer_data.get('manufacturers') and manufacturer_data.get('manufacturers').get('manufacturer'):
				manufacturers = manufacturer_data.get('manufacturers').get('manufacturer')
				if isinstance(manufacturers, list):
					manufacturers = manufacturers
				else:
					manufacturers = [manufacturers]
				for manufacturer in manufacturers:
					manufacturer_id = self.get_value_data(manufacturer.get('attrs').get('id'))
					if manufacturer_id:
						manufacturer_detail = prestashop.get('manufacturers', manufacturer_id)
						shop.create_presta_manufacturers(manufacturer_detail)
		return True

	# Not used
	# @api.one
	# def create_presta_taxes(self, tax_detail):
	# 	print("====tax_detail=====",tax_detail)

	# Not used
	# # @api.multi
	# def import_taxes(self):
	# 	for shop in self:
	# 		prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key)
	# 		tax_data = prestashop.get('taxes')
	# 		if tax_data.get('taxes') and tax_data.get('taxes').get('tax'):
	# 			taxes = tax_data.get('taxes').get('tax')
	# 		if isinstance(taxes, list):
	# 			taxes = taxes
	# 		else:
	# 			taxes = [taxes]
	# 		for tax in taxes:
	# 			tax_id = tax.get('attrs').get('id')
	# 			if tax_id:
	# 				tax_detail = prestashop.get('taxes', tax_id)
	# 				shop.create_presta_taxes(tax_detail)
	# 	return True

	# Not used
	# # @api.one
	# def create_presta_tax_rules(self, tax_rule_detail):
	# 	print("=======tax_rule_detail=====",tax_rule_detail)
	#
	#
	# # @api.multi
	# def import_tax_rules(self):
	# 	for shop in self:
	# 		prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,
	# 											  shop.prestashop_instance_id.webservice_key)
	# 		tax_rule_data = prestashop.get('tax_rules')
	# 		if tax_rule_data.get('tax_rules') and tax_rule_data.get('tax_rules').get('tax_rule'):
	# 			tax_rules = tax_rule_data.get('tax_rules').get('tax_rule')
	# 			if isinstance(tax_rules, list):
	# 				tax_rules = tax_rules
	# 			else:
	# 				tax_rules = [tax_rules]
	# 			for tax_rule in tax_rules:
	# 				tax_rule_id = tax_rule.get('attrs').get('id')
	# 				if tax_rule_id:
	# 					tax_rule_detail = prestashop.get('tax_rules', tax_rule_id)
	# 					shop.create_presta_tax_rules(tax_rule_detail)
	# 	return True


	def get_value(self, data):
		print ("get_valueeeeeeeeeeee",self,data)
		lang = self.env['prestashop.language'].search([])
		if isinstance(data, list):
			data = data
			lang_id = self.env['prestashop.language'].search([('code','=','it'), ('presta_instance_id','=', self.prestashop_instance_id.id)])
			if not lang_id:
				lang = self.env['prestashop.language'].search([])
				lang_id = self.env['prestashop.language'].search([('code', '=', lang[0].code), ('presta_instance_id', '=', self.prestashop_instance_id.id)])[0]
		else:
			data = [data]
			lang_id = self.env['prestashop.language'].search([('presta_id','=',data[0].get('attrs').get('id')), ('presta_instance_id','=', self.prestashop_instance_id.id)])[0]
		val = [i for i in data if int(i.get('attrs').get('id')) == int(lang_id.presta_id)]
		return val[0]


	# @api.multi
	def import_addresses(self):
		res_partner_obj = self.env['res.partner']
		country_obj = self.env['res.country']
		state_obj=self.env['res.country.state']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				address = prestashop.get('addresses')
				add_list =  address.get('addresses').get('address')
				if isinstance(add_list, list):
					add_list = add_list
				else:
					add_list = [add_list]
				for attrs in add_list:
					data = self.get_value_data(attrs.get('attrs').get('id'))
					if data:
						address = prestashop.get('addresses',data)
						print("addressssssssss=========>",address)

						address_ids = res_partner_obj.search([('address_id','=',self.get_value_data(attrs.get('attrs').get('id')))])
						print("address_idsssssss111111111111",address_ids)

						addr_vals = {
							# 'parent_id': data,
							'name' : self.get_value_data(address.get('address').get('firstname')) + ' ' + self.get_value_data(address.get('address').get('lastname')),
							'street': self.get_value_data(address.get('address').get('address1')),
							'street2': self.get_value_data(address.get('address').get('address2')),
							'city': self.get_value_data(address.get('address').get('city')),
							'zip': self.get_value_data(address.get('address').get('postcode')),
							'phone': self.get_value_data(address.get('address').get('phone')),
							'mobile': self.get_value_data(address.get('address').get('phone_mobile')),
							# 'customer' : self.get_value_data(address.get('address').get('id_customer'))[0],
							# 'customer' : self.get_value_data(address.get('address').get('id_customer'))[0] == '1' and address.get('address').get('id_customer') or False,
							 'customer_rank' : address.get('address').get('id_customer') != '0',

							# 'supplier': self.get_value_data(address.get('address').get('id_supplier'))[0],
							'supplier_rank': self.get_value_data(address.get('address').get('id_supplier')) == '1' and address.get('address').get('id_supplier') or False,
							# 'manufacturer': self.get_value_data(address.get('address').get('id_manufacturer'))[0],
							'manufacturer': self.get_value_data(address.get('address').get('id_manufacturer')) == '1' and address.get('address').get('id_manufacturer') or False,
							'address_id' :  self.get_value_data(address.get('address').get('id')),

						}
						print ("addr_valsssssssssssssss",addr_vals)

						country_id = int(self.get_value_data(address.get('address').get('id_country')))
						state_id =  int(self.get_value_data(address.get('address').get('id_state')))

						if country_id > 0:
							try:
								country_data=prestashop.get('countries',country_id)

								country_name=self.get_value_data(self.get_value(country_data.get('country').get('name').get('language')))
								country_code=self.get_value_data(country_data.get('country').get('iso_code'))
								country_ids=country_obj.search([('code','=',country_code)])

								if not country_ids:
									# print ("ifffnotttttt_countryyyyyy")
									country_id = country_obj.create({'name':country_name,'code':country_code})
								else:
									# print ("ifffelseeeeeeee_countryyyyyy",country_ids[0])
									country_id = country_ids[0]
								addr_vals.update({'country_id': country_id.id})
							except Exception as e:
								pass
						try:
							if state_id > 0:
								# print ("ifffffff_stateeeeeeeee",state_id)
								state_data=prestashop.get('states',state_id)
								state_name=self.get_value_data(state_data.get('state').get('name'))
								state_code=self.get_value_data(state_data.get('state').get('iso_code'))
								state_ids=state_obj.search([('code','=',state_code)])

								if not state_ids:
									# print ("iffffnottttttttt_stateeeeee")
									state_id = state_obj.create({'name':state_name,'code':state_code, 'country_id':country_ids[0].id})
								else:
									# print ("iffffesleeeeee_stateeeeee",state_ids[0])
									state_id = state_ids[0]
								addr_vals.update({'state_id' : state_id.id})
						except Exception as e:
								pass

						if not address_ids:
							parent_ids = res_partner_obj.search([('presta_id', '=', self.get_value_data(address.get('address').get('id_customer')))])
							if parent_ids:
								try:
									if not parent_ids[0].zip and not parent_ids[0].city:
										parent_ids[0].write(addr_vals)
									else:
										addr_vals.update({'parent_id': parent_ids[0].id, 'type': 'other'})
		# 											address_vals = res_partner_obj.create(addr_vals)
								except Exception as e:
									pass
								manu_id = res_partner_obj.search([])
								if manu_id:
									for menu in manu_id:
										if menu.manufacturer== True:
											menu.customer_rank = False

								self.env.cr.commit()
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'import_addresses', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
		return True

	# @api.one
	def create_presta_product(self, product, prestashop):
		# print("=====product=====>", product)
		log_id1 = False
		prod_temp_obj = self.env['product.template']
		prod_prod_obj = self.env['product.product']
		att_val_obj = self.env['product.attribute.value']
		res_partner_obj = self.env['res.partner']
		try:
			key_id = self.prestashop_instance_id
			prd_tmp_vals = {
				'name': self.get_value(product.get('name').get('language')).get('value'),
				'type': 'product',
				'list_price': self.get_value_data(product.get('price')),
				'default_code': self.get_value_data(product.get('reference')),
				'sku': self.get_value_data(product.get('reference')),
				# 'description': '',
				# 'barcode':self.get_value_data(product.get('ean13')),
				'prd_label': self.get_value(product.get('name').get('language')).get('value'),
				'wholesale_price': self.get_value_data(product.get('wholesale_price')),
				'prdct_unit_price': self.get_value_data(product.get('price')),
				'product_onsale': self.get_value_data(product.get('on_sale')),
				'product_instock': self.get_value(product.get('available_now').get('language')),
				'product_lngth': self.get_value_data(product.get('depth')),
				'product_width': self.get_value_data(product.get('width')),
				'product_wght': self.get_value_data(product.get('weight')),
				'product_hght': self.get_value_data(product.get('height')),
				'presta_id': self.get_value_data(product.get('id')),

			}
			print("===========>prd_tmp_vals>>>>>>>>>>>", prd_tmp_vals)
			if self.get_value_data(product.get('ean13')):
				prd_tmp_vals.update({'barcode': self.get_value_data(product.get('ean13'))})

			logger.info('Product Barcode ===> %s', self.get_value_data(product.get('ean13')))
			logger.info('Product ID ===> %s', self.get_value_data(product.get('id')))
			print("Barcode=========", self.get_value_data(product.get('ean13')))
			manufacturers_ids = res_partner_obj.search(
				[('presta_id', '=', self.get_value_data(product.get('id_manufacturer'))), ('manufacturer', '=', True)])
			# print("===========>manufacturers_ids>>>>>>>>>>>", manufacturers_ids)
			if manufacturers_ids:
				manufact_id = manufacturers_ids[0].id
			else:
				if self.get_value_data(product.get('id_manufacturer')) == '0':
					manufact_id = False
				else:
					manufacturer_detail = prestashop.get('manufacturers',
														 self.get_value_data(product.get('id_manufacturer')))
					manufact_id = self.create_presta_manufacturers(manufacturer_detail)[0].id
			prd_tmp_vals.update({'manufacturer_id': manufact_id})

			supplier_ids = res_partner_obj.search(
				[('presta_id', '=', self.get_value_data(product.get('id_supplier'))), ('supplier_rank', '=', True)])
			# print("===========>supplier_ids>>>>>>>>>>>", supplier_ids)
			if supplier_ids:
				supply_id = supplier_ids[0].id
			else:
				if self.get_value_data(product.get('id_supplier')) == '0':
					supply_id = False
				else:
					supplier_detail = prestashop.get('suppliers', self.get_value_data(product.get('id_supplier')))
					supply_id = self.create_presta_supplier(supplier_detail)[0].id
			prd_tmp_vals.update({'supplier_id': supply_id})
			if supply_id:
				prd_tmp_vals.update({'seller_ids': [(0, 0, {'name': supply_id})]})

			# if int(self.get_value_data(product.get('id_category_default'))) > 0:
			# 	cat_ids = category_obj.search(
			# 		[('presta_id', '=', self.get_value_data(product.get('id_category_default')))])
			# 	if cat_ids:
			# 		categ_id = cat_ids[0]
			# 	else:
			# 		vals = prestashop.get('categories', self.get_value_data(product.get('id_category_default')))
			# 		categ_id = self.create_presta_category(prestashop, vals)
			# 	prd_tmp_vals.update({'presta_categ_id': categ_id.id})
			img_ids = product.get('associations').get('images').get('image', False)
			# comment from here to   prd_tmp_vals.update({'product_img_ids': image_list})

			if img_ids:
				if isinstance(img_ids, list):
					img_ids = img_ids
				else:
					img_ids = [img_ids]
				image_list = []
				def_image_id = product.get('id_default_image')
			# for image in img_ids:
			# # try:
			# 	print ("IMAGEEEEEEEEE",image)

			# 	loc = (self.prestashop_instance_id.location).split('//')
			# 	print("=====",loc[1],product,image)
			# 	# url = "https://homepages.cae.wisc.edu/~ece533/images/airplane.png"
			# 	# file_data=urllib.request.urlopen(url).read()
			# 	# image_data = base64.encodestring(file_data)
			# 	# print ("DATAAAAAAIMAGE",type(image_data))
			# 	# from BeautifulSoup import BeautifulSoup
			# 	# import urllib3
			# 	from requests.auth import HTTPBasicAuth
			# 	url = "http://" +loc[1] + '/api/images/products/' + product.get('id') + '/' + image.get('id')
			# 	print("urk=======",url)
			# 	req = requests.get(url,str(prestashop))
			# 	re = req.urljoin(req)
			# 	# headers = {'TRN-Api-Key':key}
			# 	# req = requests.get(url,headers=headers)
			# 	print("json===",re)
			# 	print("text ====",re.text)
			# 	dddd
			# 	# fffff
			# 	# response = requests.get(url)
			# 	response = requests.get(url,key)

			#  #          auth = HTTPBasicAuth(key_id, key))
			# 	# print("text formate",response)
			# 	# ppri
			# 	print("jjjjj===",response)
			# 	ddddds

			# 	# headers = {}
			# 	# headers['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"
			# 	re = urllib.request.urlopen(url)
			# 	# res = urllib.request.Request(url, data=None, headers={}, origin_req_host=None, unverifiable=False, method=None)
			# 	print("req====",re)
			# 	# # dddd
			# 	# response = requests.get(res)
			# 	# h = response.state_code
			# 	# print("jjjjj===",h)
			# 	# hhhhhh
			# 	# resp = urllib.request.urlopen(req)
			# 	# respData = resp.read()

			# 	ddddddd

			# 	# if def_image_id == image.get('id'):
			# 	#     print ("iiiiiiiiiiiiii")
			# 	#     cccc
			# 	#     print ("image data",image_data)
			#   		# prd_tmp_vals.update({'prest_img_id': image_data})
			# 	# print ("image.get('id')))))))))))))))",image.get('id'))

			# 	image_list.append((0, 0, {'url': url,
			# 							  # 'prest_img_id': image.get('id'),
			# 							  'link': True,
			# 							  'name': image.get('id'),
			# 	}))
			# 	print("v=====",image_list)

			# 	# except Exception as e:
			# 	#     if self.env.context.get('log_id'):
			# 	#         log_id =  self.env.context.get('log_id')
			# 	#         self.env['log.error'].create({'log_description': str(e) + " While Getting Image of %s"%( image.get('id')), 'log_id': log_id})
			# 	#     else:
			# 	#         log_id = self.env['prestashop.log'].create({'all_operations':'import_products','error_lines': [(0,0, {'log_description': str(e)+" While Getting Image info of %s"%( image.get('id'))})]})
			# 	#         log_id1 = log_id.id
			# 	    #         self = self.with_context(log_id = log_id.id)

			# 	if len(image_list) > 0:
			# 		print("image_data========",image_data)
			# 		prd_tmp_vals.update({'image_1920':image_data})
			# 		print("prod_prod_obj====",prd_tmp_vals.get('image_1920'))
			# dddddd
			# prd_tmp_vals.update({'product_img_ids': image_list,'image_1920':image_data})

			reference = product.get('reference')
			attribute_line_ids = []
			atttibute_lines_dict = {}
			print("===========>product.associations>>>>>>>>>>>",
				  product.get('associations').get('product_option_values').get('product_option_value'))
			if product.get('associations').get('product_option_values').get('product_option_value'):
				data = product.get('associations').get('product_option_values').get('product_option_value')
			else:
				data = product.get('associations').get('product_option_values')

			if data:
				if isinstance(data, dict):
					data = [data]
				for att_val in data:
					if att_val.get('value') in ('', '0'):
						continue
					value_ids = att_val_obj.search([('presta_id', '=', self.get_value_data(att_val.get('id')))])
					print("===========>value_ids>>>>>>>>>>>", value_ids)

					# if not value_ids:
					# 	raise UserError(("Please Import Product Attributes first."))

					if value_ids:
						v_id = value_ids[0]
						# print("v_id======",v_id)
						if v_id.attribute_id.id in atttibute_lines_dict:
							if v_id.id not in atttibute_lines_dict.get(v_id.attribute_id.id):
								atttibute_lines_dict.get(v_id.attribute_id.id).append(v_id.id)
						else:

							atttibute_lines_dict.update({v_id.attribute_id.id: [v_id.id]})
					# print("atttibute_lines_dict===",atttibute_lines_dict)
				for i in atttibute_lines_dict.keys():
					attribute_line_ids.append(
						(0, 0, {'attribute_id': i, 'value_ids': [(6, 0, atttibute_lines_dict.get(i))]}))
				prd_tmp_vals.update({'attribute_line_ids': attribute_line_ids})
				print("prd_tmp_vals====", prd_tmp_vals)
			prod_ids = False
			categ_list = []
			# categories = product.get('associations').get('categories').get('category')
			# if isinstance(categories, dict):
			#     categories = [categories]
			#
			# for category in categories:
			#     cat_ids = category_obj.search([('presta_id', '=', category.get('id'))])
			#     if cat_ids:
			#         categ_list.append(cat_ids[0].id)
			#     else:
			#         vals = prestashop.get('categories', category.get('id'))
			#         cat_id = self.create_presta_category(prestashop, vals)
			#         categ_list.append(cat_id[0].id)
			# prd_tmp_vals.update({'presta_categ_ids': [(6, 0, categ_list)]})
			# print("self.get_value_data(product.get('reference'))[0]==",self.get_value_data(product.get('reference')))
			#	if self.get_value_data(product.get('reference')):
			prod_ids = prod_temp_obj.search([('presta_id', '=', self.get_value_data(product.get('id')))])
			print("===========>prod_ids>>>>>>>>>>>", prod_ids)
			# previously we searched with presta_id
			# else:
			#     prod_ids = prod_temp_obj.search([('presta_id', '=', product.get('id'))])
			#     print "presta_id found===========>",prod_ids
			if prod_ids:
				p_id = prod_ids[0]
				# write attributes
				if prd_tmp_vals.get('attribute_line_ids'):
					for each in prd_tmp_vals.get('attribute_line_ids'):
						attribute_ids = self.env['product.template.attribute.line'].search(
							[('product_tmpl_id', '=', p_id.id), ('attribute_id', '=', each[2].get('attribute_id'))])
						if attribute_ids:
							for val_at in each[2].get('value_ids')[0][2]:
								if val_at not in attribute_ids[0].value_ids.ids:
									attribute_ids[0].write({'value_ids': [(6, 0, [val_at])]})
						else:
							self.env['product.template.attribute.line'].create(
								{'attribute_id': each[2].get('attribute_id'), 'product_tmpl_id': p_id.id,
								 'value_ids': each[2].get('value_ids')})
					if prd_tmp_vals.get('attribute_line_ids'):
						prd_tmp_vals.pop('attribute_line_ids')
				p_id.write(prd_tmp_vals)
				self.env.cr.execute(
					"select product_id from product_templ_shop_rel where product_id = %s and shop_id = %s" % (
						prod_ids.id, self.id))
				prod_data = self.env.cr.fetchone()
				if prod_data == None:
					self.env.cr.execute("insert into product_templ_shop_rel values(%s,%s)" % (prod_ids.id, self.id))

			if not prod_ids:
				print("product=======not>>>>>>>>>>>found", prd_tmp_vals)
				prod_id = prod_temp_obj.create(prd_tmp_vals)
				logger.info('Producrt Created ===> %s', prod_id.id)
				self.env.cr.execute(
					"select product_id from product_templ_shop_rel where product_id = %s and shop_id = %s" % (
						prod_id.id, self.id))
				prod_data = self.env.cr.fetchone()
				if prod_data == None:
					q1 = "insert into product_templ_shop_rel values(%s,%s)" % (prod_id.id, self.id)
					self.env.cr.execute(q1)

				if product.get('associations').get('combinations').get('combination', False):
					comb_l = product.get('associations').get('combinations').get('combination', False)
					print("===========>ifffffffffffffffffcomb_lcomb_l>>>>>>>>>>>", comb_l)
					# 			else:
					# 				comb_l = product.get('combinations').get('combination')
					# 				print("===========>elseeeeeeeeeeeeeecomb_lcomb_l>>>>>>>>>>>",comb_l)
					c_val = {}
					if comb_l:
						if isinstance(comb_l, list):
							comb_l = comb_l
						else:
							comb_l = [comb_l]

						for comb in comb_l:
							print("comb==========comb=======_id===", self.get_value_data(comb.get('id')))

							combination_dict = prestashop.get('combinations', self.get_value_data(comb.get('id')))
							print("===========>combination_dictcombination_dict>>>>>>>>>>>", combination_dict)
							value_list = []
							value_comb_ids = combination_dict.get('combination').get('associations').get(
								'product_option_values').get('product_option_value')
							print("===========>value_comb_ids>>>>>>>>>>>", value_comb_ids)
							if value_comb_ids == None:
								value_comb_ids = False
							else:
								if isinstance(value_comb_ids, list):
									value_comb_ids = value_comb_ids
								else:
									value_comb_ids = [value_comb_ids]
								# print "value_comb_ids",value_comb_ids
								for each in value_comb_ids:
									val_id = self.get_value_data(each.get('id'))

									value_list.append(val_id)
									print("value_list====", value_list)
								# fffff
								print("-----", self.get_value_data(value_list))

								attr_val_ids = att_val_obj.search(
									[('presta_id', 'in', self.get_value_data(value_list))])
								print("===========attr_val_idsattr_val_idsattr_val_ids>>>>>>>>>>>>>>>>>.",
									  attr_val_ids[0].name,
									  self.get_value_data(value_list))
								print("attr_val_ids=====", attr_val_ids)
								# ffffffffffff
								product_ids = prod_prod_obj.search(
									[('product_tmpl_id.presta_id', '=',
									  self.get_value_data(combination_dict.get('combination').get('id_product')))])
								print("product_idsproduct_idsincombbbbbbbbbb", product_ids)
								value_list
								prod_id_var = False
								#                     prod_id_var = prd_tmp_vals.pop('barcode', None)
								if product_ids:

									for product_data in product_ids:
										# if not product_data.combination_id
										print("product_data========1111",
											  product_data.product_template_attribute_value_ids.product_attribute_value_id[
												  0].presta_id, product_ids, product_data)
										# oooooooooo
										print("combination===id=======", self.get_value_data(comb.get('id')))
										# gggggg
										# print("------",self.get_value_data(value_list))

										# new = product_data.search([('product_template_attribute_value_ids.presta_id','in',
										# str(self.get_value_data(value_list)))])
										# print("new=====",new)

										prod_val_ids = product_data.product_template_attribute_value_ids.product_attribute_value_id
										k = []
										for red in prod_val_ids:
											print("prod_val_ids===", prod_val_ids)
											k.append(red.presta_id)
										# ccccs
										print("check both data---", k, self.get_value_data(value_list))
										# cccc
										res = k
										rles = sorted(res, key=int)
										print("res====", rles)
										t = self.get_value_data(value_list)
										if rles == t:
											print("combination_dict====", combination_dict)
											# dddd
											c_val.update({

												'combination_price': float(
													self.get_value_data(
														combination_dict.get('combination').get('price', 0.0))),
												'combination_id': self.get_value_data(comb.get('id')),
												'default_code':
													self.get_value_data(
														combination_dict.get('combination').get('reference')),

											})
											print("c_val=======", c_val)
											# if self.get_value_data(combination_dict.get('combination').get('ean13')):
											# 	c_val.update({'barcode':self.get_value_data(combination_dict.get('combination').get('ean13'))})

											product_data.write(c_val)
											print("product_data====11", product_data.combination_id)
											print("product_data====11", product_data.combination_price)
											print("product_data====11", product_data.default_code)
											print("product_data====11", product_data.default_code)
											print("product_data===========orders", product_ids)
								# if self.get_value_data(combination_dict.get('combination').get('reference')):
								# c_val.update({'default_code':self.get_value_data(combination_dict.get('combination').get('reference'))})
								# product_data.write(c_val)
								# get_val_ids = attr_val_ids.ids
								# get_val_ids.sort()
								# if get_val_ids == prod_val_ids:
								# 	prod_id_var = product_data
								# 	value_ids = product_data.product_template_attribute_value_ids
								# 	break
					# print("combination_id=======",self.get_value_data(comb.get('id')))

					# print("product_data====",c_val)
					# print("c_val======",c_val,product_data)
					# # dddd
					# # if prod_id_var:
					# product_ids[0].write(c_val)
					# 	print("c_valc_valc_val d end==>", c_val)
			else:
				prod_id = prod_ids[0]
			# print ("prod_id----------------->",prod_id)
			self.env.cr.commit()
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_products', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		return True

	# @api.multi
	def import_products(self):
		print("====import_products====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			ctx = {}
			last_import_product = shop.last_prestashop_product_import_date
			if last_import_product:
				last_imported_customer_products = last_import_product.date()
				products = prestashop.get('products',options={'filter[date_upd]': last_imported_customer_products, 'date': '1'})
			else:
				product = prestashop.get('products')
				if product.get('products') and product.get('products').get('product'):
					for attrs in product.get('products').get('product'):
						data = self.get_value_data(attrs.get('attrs').get('id'))
						if data:
							#                       try:
							product_data = prestashop.get('products',data)
							data = self.with_context(self.env.context.copy()).create_presta_product(
								product_data.get('product'), prestashop)
							if data:
								self = self.with_context(log_id=data)
		shop.write({'last_prestashop_product_import_date': datetime.now()})
		self.env.cr.commit()
		return True


#Manish img not using this code
	# @api.multi
	def import_products_images(self):
		print("====import_products_images====>")
		prod_templ_obj=self.env['product.template']
		product_obj=self.env['product.product']
		# product_img_obj=self.env['product.images.new']
		prest_categ_obj=self.env['prestashop.category']
		prod_attr_val_obj=self.env['product.attribute.value']
		prod_attr_obj=self.env['product.attribute']

		prestashop=self.presta_connect()
		key_id=self.prestashop_instance_id
		key=key_id.webservice_key
		for shop in self:
			last_import_date=self.last_prestashop_product_import_date
			if last_import_date:
				last_imported_date = last_import_date.date()
				products= prestashop.get('products',options={'filter[date_upd]':last_imported_date,'date':'1','filter[id_shop_default]': shop.presta_id})
				# 'filter[product_option_value]': self.combination_id
			else:
				products= prestashop.get('products',options={'limit': 3000})
			print('--------------=====',products)
			prod=ET.tostring(products)
			prod_list=[int(product.get('id')) for product in products.findall('products/product')]
			prod_list.sort()
			print('prod_list--------------',prod_list)
			for prd_ids in prod_list:
				prod_data= prestashop.get('products',prd_ids)
				# , options = {'filter[product_option_value]': self.combination_id}
				print('prod_data------------',prod_data)
				print('prd_ids------------',prestashop)
				if prod_data:
					for prod_pos in prod_data.findall('./api/images/products'):
						print('-=-=-==============',prod_pos.get('{http://www.w3.org/1999/xlink}href'))

					for prod_pos in prod_data.findall('./product'):
						print('prod_pos------------',prod_pos)
						combination_img=prod_pos.findall('./associations/product_option_values/product_option_value')
						#Product images per product:
						tmpl_ids = prod_templ_obj.search([('presta_id','=',prd_ids)])
						for image in prod_pos.findall('./associations/images/image'):
							print('img----------------------',image.get('{http://www.w3.org/1999/xlink}href'))
							print('image---------',image)
							print('image--image-------',type(image))

						image_lst=[image.get('{http://www.w3.org/1999/xlink}href') for image in prod_pos.findall('./associations/images/image')]
						image_ids_list=[]
						print('image_lst--------------',image_lst)
						for image_ids in image_lst:
							# new_image_url=image_ids[0:7]+key+':@'+image_ids[7:]
							new_image_url=image_ids
							print('----------tmpl_ids-----',tmpl_ids)
							print('----------new_image_url-----',new_image_url)
							file_contain = urllib.request.urlopen(new_image_url).read()
							if file_contain and not tmpl_ids:
								image = base64.b64encode(file_contain)
								image_val=(0,0,{'image_url':image_ids,'image':image})
								image_ids_list.append(image_val)
							if file_contain and tmpl_ids:
								image = base64.b64encode(file_contain)
								image_prd_ids=product_img_obj.search([('product_imgs','=',tmpl_ids[0].id),('image_url','=',image_ids)])
								if not image_prd_ids:
									image_val=(0,0,{'image_url':image_ids,'image':image})
									# prest_img_id
									image_ids_list.append(image_val)
						if image_ids_list:
							tmpl_ids.write({'product_img_ids':image_ids_list or False,
											'image': image_ids_list[0][2].get('image')})

		shop.write({'last_prestashop_product_import_date':datetime.today()})
		self.env.cr.commit()
		return True


	# @api.one
	def createInventory(self, inv_res, lot_stock_id, prestashop):
		print("inside createInventory", inv_res)
		product_obj = self.env['product.product']
		product_temp_obj = self.env['product.template']
		inv_wiz = self.env['stock.change.product.qty']
		quantity = self.get_value_data(inv_res.get('quantity'))
		try:
			if self.get_value_data(inv_res.get('id_product_attribute')) == '0':
				product_ids = product_obj.search([('product_tmpl_id.presta_id', '=', self.get_value_data(inv_res.get('id_product')))])
				if product_ids:
					child_ids = product_obj.search([('product_tmpl_id', '=', product_ids[0].product_tmpl_id.id)])
					if len(child_ids) > 1:
						return True
			else:
				product_ids = product_obj.search([('combination_id', '=', inv_res.get('id_product_attribute'))])
			if not product_ids:
				prod_data_tmpl = prestashop.get('products', self.get_value_data(inv_res.get('id_product')))
				self.create_presta_product(prod_data_tmpl.get('product'), prestashop)
				if self.get_value_data(inv_res.get('id_product_attribute')) == '0':
					product_ids = product_obj.search([('product_tmpl_id.id', '=', self.get_value_data(inv_res.get('id_product')))])
					if product_ids:
						child_ids = product_obj.search([('product_tmpl_id', '=', product_ids[0].product_tmpl_id.id)])
						if len(child_ids) > 1:
							return True
				else:
					product_ids = product_obj.search([('combination_id', '=', self.get_value_data(inv_res.get('id_product_attribute')))])
			if product_ids:
				self.env.cr.execute("select product_prod_id from product_prod_shop_rel where product_prod_id = %s and shop_id = %s" % (product_ids[0].id, self.id))
				prod_data = self.env.cr.fetchone()
				if prod_data is None:
					self.env.cr.execute("insert into product_prod_shop_rel values(%s,%s)" % (product_ids[0].id, self.id))
				print("quantityquantity====quantity", quantity,product_ids[0].id,product_ids)
				inv_wizard = inv_wiz.create({
					'product_tmpl_id': product_ids[0].product_tmpl_id.id,
					'new_quantity': quantity,
					'product_id': product_ids[0].id,
				})
				inv_wizard.change_product_qty()
				self.env.cr.commit()
				return True
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_inventory', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context

	# @api.multi
	def import_product_inventory(self):
		print("=====import_product_inventoryyyyyyy======")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			last_import_inventory = shop.last_prestashop_inventory_import_date
			if last_import_inventory:
				last_imported_inventory = last_import_inventory.date()
				products = prestashop.get('products', options={'filter[date_upd]': last_imported_inventory, 'date': '1'}, )
			else:
				products = prestashop.get('products')
				products = products.get('products') and products.get('products').get('product')
				if products:
					if isinstance(products, list):
						products = products
					else:
						products = [products]

					prod_ids = [self.get_value_data(prod.get('attrs').get('id')) for prod in products]
					h = str(prod_ids).replace(',', '|')
					stock_data = prestashop.get('stock_availables')
					stocks = stock_data.get('stock_availables').get('stock_available')
					if isinstance(stocks, list):
						stocks = stocks
					else:
						stocks = [stocks]
					for stock in stocks:
						stock_id = self.get_value_data(stock.get('attrs').get('id'))
						if stock_id:
							stock_detail = prestashop.get('stock_availables', stock_id)

							if self.get_value_data(stock_detail.get('stock_available').get('id_product')) not in prod_ids:
								continue
							shop.createInventory(stock_detail.get('stock_available'),shop.warehouse_id.lot_stock_id.id, prestashop)
			shop.write({'last_prestashop_inventory_import_date': datetime.today()})
		return True


	# @api.one
	def create_carrier(self, carrier):
		print ("====create_carrier====",carrier)
		carrier_obj = self.env['delivery.carrier']
		product_obj = self.env['product.product']
		try:
			product_ids = product_obj.search([('name', '=', self.get_value_data(carrier.get('name')))])
			if product_ids:
				product_id = product_ids[0]
			else:
				product_id = product_obj.create({'name': self.get_value_data(carrier.get('name'))})
			carr_vals = {
				'name': self.get_value_data(carrier.get('name')),
				# 'free_if_more_than': int(self.get_value_data(carrier.get('is_free'))),
				'fixed_price': int(self.get_value_data(carrier.get('shipping_external'))),
				'product_id': product_id.id,
				'presta_id': self.get_value_data(carrier.get('id')),
			}
			car_ids = carrier_obj.search([('presta_id', '=', self.get_value_data(carrier.get('id')))])
			if not car_ids:
				carrier_id = carrier_obj.create(carr_vals)
				logger.info('created carrier ===> %s', carrier_id.id)
			else:
				carrier_id = car_ids[0]
			self.env.cr.commit()
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_carriers', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context

		return True


	# @api.multi
	def import_carriers(self):
		print ("===import_carriers====>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			ctx={}
			carriers = prestashop.get('carriers')
			if carriers.get('carriers') and carriers.get('carriers').get('carrier'):
				carriers = carriers.get('carriers').get('carrier')
			if isinstance(carriers, list):
				carriers = carriers
			else:
				carriers = [carriers]
			for carrier in carriers:
				carrier_id = self.get_value_data(carrier.get('attrs').get('id'))
				if carrier_id:
					carrier_detail = prestashop.get('carriers', carrier_id)
					self.with_context(ctx).create_carrier(carrier_detail.get('carrier'))

			shop.write({'last_prestashop_carrier_import_date': datetime.today()})
			return True

	#workflow of order
	def manageOrderWorkflow(self, saleorderid, order_detail, status):

		print ("===========manageOrderWorkflow==========")

		invoice_obj = self.env['account.move']
		# invoice_refund_obj = self.env['account.move.refund']
		return_obj = self.env['stock.return.picking']
		return_line_obj = self.env['stock.return.picking.line']
		if status.name == 'Canceled':
			if saleorderid.state in ['draft']:
				saleorderid.action_cancel()

			if saleorderid.state in ['progress', 'done', 'manual']:
				invoice_ids = saleorderid.invoice_ids
				for invoice in invoice_ids:
					refund_ids = invoice_obj.search([('invoice_origin', '=', invoice.number)])
					# print  "==refund_ids==>",refund_ids
					if not refund_ids:
						if invoice.state == 'paid':
							refund_invoice_id = invoice_refund_obj.create(dict(
								description='Refund To %s' % (invoice.partner_id.name),
								date=datetime.date.today(),
								filter_refund='refund'
							))
							refund_invoice_id.invoice_refund()
							saleorderid.write({'is_refund': True})
						else:
							invoice.action_cancel()

				for picking in saleorderid.picking_ids:
					if picking.state not in ('done'):
						picking.action_cancel()
					else:
						ctx = self._context.copy()
						ctx.update({'active_id': picking.id})
						res = return_obj.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists'])
						res.update({'invoice_state': '2binvoiced'})
						return_id = return_obj.with_context(ctx).create({'invoice_state': 'none'})
						for record in res['product_return_moves']:
							record.update({'wizard_id': return_id.id})
							return_line_obj.with_context(ctx).create(record)

						pick_id_return, type = return_id.with_context(ctx)._create_returns()
						pick_id_return.force_assign()
						pick_id_return.action_done()
			saleorderid.action_cancel()
			return True

		# Make Order Confirm
		#if validate order is activated in workflow
		if self.workflow_id.validate_order:
			fffffff
			if saleorderid.state in ['draft']:
				saleorderid.action_confirm()

		# if complete shipment is activated in workflow
		if self.workflow_id.complete_shipment:
			print("complete shipment")
			if saleorderid.state in ['draft']:
				saleorderid.action_confirm()
			for picking_id in saleorderid.picking_ids:

				# If still in draft => confirm and assign
				if picking_id.state == 'draft':
					picking_id.action_confirm()
					picking_id.action_assign()

				if picking_id.state == 'confirmed':
					picking_id.force_assign()
				picking_id.do_transfer()

		# if create_invoice is activated in workflow
		if self.workflow_id.create_invoice:
			if not saleorderid.invoice_ids:
				invoice_ids = saleorderid.action_invoice_create()
				invoice_ids = invoice_obj.browse(invoice_ids)
				invoice_ids.write({'is_prestashop': True})

		# if validate_invoice is activated in workflow
		if self.workflow_id.validate_invoice:
			if saleorderid.state == 'draft':
				saleorderid.action_confirm()

			if not saleorderid.invoice_ids:
				invoice_ids = saleorderid.action_invoice_create()
				invoice_ids = invoice_obj.browse(invoice_ids)
				invoice_ids.write({'is_prestashop': True})

			for invoice_id in saleorderid.invoice_ids:
				invoice_id.write({
					'total_discount_tax_excl': self.get_value_data(order_detail.get('total_discounts_tax_excl')),
					'total_discount_tax_incl': self.get_value_data(order_detail.get('total_discounts_tax_incl')),
					'total_paid_tax_excl': self.get_value_data(order_detail.get('total_paid_tax_excl')),
					'total_paid_tax_incl': self.get_value_data(order_detail.get('total_paid_tax_incl')),
					'total_products_wt': self.get_value_data(order_detail.get('total_products_wt')),
					'total_shipping_tax_excl': self.get_value_data(order_detail.get('total_shipping_tax_excl')),
					'total_shipping_tax_incl': self.get_value_data(order_detail.get('total_shipping_tax_incl')),
					'total_wrapping_tax_excl': self.get_value_data(order_detail.get('total_wrapping_tax_excl')),
					'total_wrapping_tax_incl': self.get_value_data(order_detail.get('total_wrapping_tax_incl')),
					'is_prestashop': True,
				})

				if invoice_id.state == 'draft':
					invoice_id.action_invoice_open()

		# if register_payment is activated in workflow
		if self.workflow_id.register_payment:
			if saleorderid.state == 'draft':
				saleorderid.action_confirm()
			if not saleorderid.invoice_ids:
				invoice_ids = saleorderid.action_invoice_create()
				invoice_ids = invoice_obj.browse(invoice_ids)
				invoice_ids.write({'is_prestashop': True})

			for invoice_id in saleorderid.invoice_ids:
				invoice_id.write({
					'total_discount_tax_excl': self.get_value_data(order_detail.get('total_discounts_tax_excl')),
					'total_discount_tax_incl': self.get_value_data(order_detail.get('total_discounts_tax_incl')),
					'total_paid_tax_excl': self.get_value_data(order_detail.get('total_paid_tax_excl')),
					'total_paid_tax_incl': self.get_value_data(order_detail.get('total_paid_tax_incl')),
					'total_products_wt': self.get_value_data(order_detail.get('total_products_wt')),
		'total_shipping_tax_excl': self.get_value_data(order_detail.get('total_shipping_tax_excl')),
					'total_shipping_tax_incl': self.get_value_data(order_detail.get('total_shipping_tax_incl')),
					'total_wrapping_tax_excl': self.get_value_data(order_detail.get('total_wrapping_tax_excl')),
					'total_wrapping_tax_incl': self.get_value_data(order_detail.get('total_wrapping_tax_incl')),
					'is_prestashop': True,
				})
				if invoice_id.state == 'draft':
					invoice_id.action_invoice_open()

				if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
					invoice_id.pay_and_reconcile(
						self.workflow_id and self.sale_journal or self.env['account.journal'].search(
							[('type', '=', 'bank')], limit=1), invoice_id.amount_total)
		return True

	# @api.one
	def manageOrderLines(self, orderid, order_detail, prestashop):
		# vvvvvvvvv
		print("===========manageOrderLines_order_detail==========", order_detail,order_detail.get('total_discounts'))
		# print ("===========prestashop==========",prestashop)
		sale_order_line_obj = self.env['sale.order.line']
		prod_attr_val_obj = self.env['product.attribute.value']
		prod_templ_obj = self.env['product.template']
		product_obj = self.env['product.product']
		lines = []
		order_rows = order_detail.get('associations').get('order_rows').get('order_row')
		# print("===========order_rows==========", order_rows)
		# dddddd
		if isinstance(order_rows, list):
			order_rows = order_rows
		else:
			order_rows = [order_rows]
		for child in order_rows:
			line = {
				'price_unit': str(self.get_value_data(child.get('unit_price_tax_incl'))),
				'name': self.get_value_data(child.get('product_name')),
				'product_uom_qty': str(self.get_value_data(child.get('product_quantity'))),
				'order_id': orderid.id,
				'tax_id': False,
			}
			# print("===========line==========", line)

			#discount details
			# discount = 0.0
			# discou = order_detail.get('total_discounts')
			# print("discou====",discou,type(discou))
			# discou = discou.get('value')
			# print("discou===",discou)
			# if float(discou) > 0.0:
			# 	line.update({'discount': discou})
			# print('------',child.get('product_attribute_id'))
			if self.get_value_data(child.get('product_attribute_id')) != '0':
				value_ids = []
				value_list = []
				# print("====child.get('product_attribute_id').get('value')========>", child.get('product_attribute_id'))
				# 			try:
				combination = prestashop.get('combinations', self.get_value_data(child.get('product_attribute_id')))
				# print("====combination========>", combination)
				value_ids = combination.get('combination').get('associations').get('product_option_values').get(
					'product_option_value')
				# print("====value_ids========>", value_ids)
				if isinstance(value_ids, list):
					value_ids = value_ids
				else:
					value_ids = [value_ids]
				for value_id in value_ids:
					values = self.get_value_data(value_id.get('id'))
					value_ids = prod_attr_val_obj.search([('presta_id', '=', values)])
					sa = value_list.append(value_ids.id)
				# values = self.get_value_data(value_ids.get('id'))[0]
				# print("====values========>", values)
				# if  value_ids.get('id') :
				# value_ids = prod_attr_val_obj.search([('presta_id', '=', self.get_value_data(values)[0])])
				temp_ids = prod_templ_obj.search(
					[('presta_id', '=', self.get_value_data(combination.get('combination').get('id_product')))])

				# print("====temp_ids======",temp_ids)
				if not temp_ids:
					prod_data_tmpl = prestashop.get('products', self.get_value_data(
						combination.get('combination').get('id_product')))
					temp_ids = self.create_presta_product(prod_data_tmpl.get('product'), prestashop)

				if temp_ids:
					# print("product_ids====",self.get_value_data(combination.get('combination').get('id_product')))
					product_ids = product_obj.search([('id','=',self.get_value_data(combination.get('combination').get('id_product')))])
					# print("product_ids============",product_ids)

					# cccccc
					# print("product_ids====",self.get_value_data(
					# 	combination.get('combination').get('id_product')))
					for product_id in product_ids:
						# bbbb
						if product_id.product_template_attribute_value_ids == prod_attr_val_obj.browse(
								value_list) and product_id.product_tmpl_id == temp_ids[0]:
							product_ids = product_id
							# eeeeee
					if product_ids:
						# jjjj
						# print("====product_ids[0].id====",product_ids[0].id)
						line.update({'product_id': product_ids[0].id, 'product_uom': product_ids[0].uom_id.id})
					else:
						prod_data = prestashop.get('products', self.get_value_data(
							combination.get('combination').get('id_product')))
						tmpl_id = self.create_presta_product(prod_data.get('product'), prestashop)[0]
						product_ids = product_obj.search([('product_tmpl_id', '=', tmpl_id[0].id)])
						line.update({'product_id': product_ids[0].id, 'product_uom': product_ids[0].uom_id.id})
			# 			except:
			# 				pass
			else:
				temp_ids = prod_templ_obj.search([('presta_id', '=', self.get_value_data(child.get('product_id')))])
				# print("temp_ids-----", temp_ids)
				# check for non variant product
				if temp_ids:
					product_ids = product_obj.search([('product_tmpl_id', '=', temp_ids[0].id)])
					# print("============tempproduct_ids==>>>>>>>>>>", product_ids)
					# check for non variant products by product_tmpl_ids if multiple found
					if product_ids:
						line.update({'product_id': product_ids[0].id, 'product_uom': product_ids[0].uom_id.id})
						# print("line=====>>>>>>", line)
					else:
						prod_data = prestashop.get('products', self.get_value_data(child.get('product_id')))
						# changed to product_id
						tmpl_id = self.create_presta_product(prod_data.get('products'), prestashop)[0].id
						product_ids = product_obj.search([('product_tmpl_id', '=', tmpl_id)])
						line.update({'product_id': product_ids[0].id, 'product_uom': product_ids[0].uom_id.id})
				else:
					try:
						new_product_data = prestashop.get('products', self.get_value_data(child.get('product_id')))
						new_tmpl_id = self.create_presta_product(new_product_data.get('product'), prestashop)[0].id
						new_product_ids = product_obj.search([('product_tmpl_id', '=', new_tmpl_id)])
						line.update({'product_id': new_product_ids[0].id, 'product_uom': new_product_ids[0].uom_id.id})
						# print("============line==>>>>>>>>>>", line)
					except:
						p_ids = product_obj.search([('default_code', '=', 'RMVPRD')])
						if not p_ids:
							pid = product_obj.create({'name': 'Removed Product', 'default_code': 'RMVPRD'})
						else:
							pid = p_ids[0]
						line.update({'product_id': pid[0].id, 'product_uom': pid[0].uom_id.id})
						pass

			if line.get('product_id'):
				# print("===line===")
				line_ids = sale_order_line_obj.search([('product_id', '=', self.get_value_data(line.get('product_id'))),('order_id', '=', orderid.id)])
				print("=========line_ids____",line_ids)
				if not line_ids:
					sale_order_line_obj.create(line)

		if order_detail.get('total_discounts'):
			discoun = order_detail.get('total_discounts')
			total = float(orderid.amount_total)- float(discoun)
			orderid.write({'amount_total':total})

			# Shipment fees and fields
		ship = float(self.get_value_data(order_detail.get('total_shipping')))
		if ship and ship > 0:
			sline = {
				'product_id': self.shipment_fee_product_id.id,
				'product_uom': self.shipment_fee_product_id.uom_id.id,
				'price_unit': ship,
				'product_uom_qty': 1,
				'order_id': orderid.id
			}
			sline_ids = sale_order_line_obj.search([('product_id', '=', self.get_value_data(sline.get('product_id'))),('order_id', '=', orderid.id)])
			if not sline_ids:
				sale_order_line_obj.create(sline)
			else:
				sline_ids[0].write({'price_unit': sline_ids[0].price_unit + ship})

		# wrapping fees and fields
		wrapping = float(self.get_value_data(order_detail.get('total_wrapping', 0)))
		if wrapping and wrapping > 0:
			wline = {
				'product_id': self.gift_wrapper_fee_product_id.id,
				'product_uom': self.gift_wrapper_fee_product_id.uom_id.id,
				'price_unit': wrapping,
				'product_uom_qty': 1,
				'name': self.get_value_data(order_detail.get('gift_message')),
				'order_id': orderid.id
			}
			wline_ids = sale_order_line_obj.search(
				[('product_id', '=', self.get_value_data(wline.get('product_id'))),
				 ('order_id', '=', orderid.id)])
			if not wline_ids:
				sale_order_line_obj.create(wline)
			else:
				wline_ids[0].write({'price_unit': wline_ids[0].price_unit + wrapping,
									'name': wline_ids[0].name + self.get_value_data(wline.get('name'))})


	# @api.one
	def create_presta_order(self, order_detail, prestashop):
		# gggg
		sale_order_obj = self.env['sale.order']
		res_partner_obj = self.env['res.partner']
		carrier_obj = self.env['delivery.carrier']
		status_obj = self.env['presta.order.status']
		order_vals = {}
		try:
			partner_ids = res_partner_obj.search([('presta_id', '=', self.get_value_data(order_detail.get('id_customer')))])
			# print("sale order part>>>>>>>>>>>>>>>>",self.get_value_data(order_detail.get('id_customer')),partner_ids)

			if partner_ids:
				order_vals.update({'partner_id': partner_ids[0].id})
			else:

				# try:
				cust_data = prestashop.get('customers', self.get_value_data(order_detail.get('id_customer')))
				# print("cust_data========>>>>>>>",cust_data)

				customer = self.create_customer(cust_data,prestashop)
				# except:
				customer = [self.partner_id]
					# pass
				order_vals.update({'partner_id': customer[0].id})

			state_ids = status_obj.search([('presta_id', '=', self.get_value_data(order_detail.get('current_state')))])
			if state_ids:
				st_id = state_ids[0]
			else:
				orders_status_lst = prestashop.get('order_states', self.get_value_data(order_detail.get('current_state')))
				st_id = status_obj.create({
					'name':  self.get_value_data(self.get_value(orders_status_lst.get('order_state').get('name').get('language'))),
					'presta_id': self.get_value_data(order_detail.get('current_state')),
					})

			a = self.get_value_data(order_detail.get('payment'))
			p_mode = False
			if a[0] == 'Bank wire':
				p_mode = 'bankwire'
			elif a[0] == 'Payments by check':
				p_mode = 'cheque'
			elif a[0] == 'Bank transfer':
				p_mode = 'banktran'
			order_vals.update({'reference': self.get_value_data(order_detail.get('reference')),
	# 					   'presta_payment_mode' : self.get_value_data(order_detail.get('module'))[0],
						   'presta_id' : self.get_value_data(order_detail.get('id')),
						   # 'shop_id' : self[0].id,
						   'warehouse_id': self.warehouse_id.id,
						   'presta_order_ref': self.get_value_data(order_detail.get('reference')),
						   # 'carrier_prestashop': order_detail.get('id_carrier'),
						   'pretsa_payment_mode': p_mode,
						   'pricelist_id': self.pricelist_id.id,
						   'name': 'SO000' + self.get_value_data(order_detail.get('id')),
						   'order_status' : st_id.id,
						   'shop_id': self.id,
						   'presta_order_date': self.get_value_data(order_detail.get('date_add')),
						   # 'id_shop_group':1,
							})
			if self.workflow_id.picking_policy:
				order_vals.update({'picking_policy' : self.workflow_id.picking_policy})

			carr_ids =carrier_obj.search([('presta_id','=', self.get_value_data(order_detail.get('id_carrier')))])
			if int(self.get_value_data(order_detail.get('id_carrier'))) > 0:
				if carr_ids:
					order_vals.update({'carrier_prestashop': carr_ids[0].id})
				else:
					try:
						carrier_data = prestashop.get('carriers',  self.get_value_data(order_detail.get('id_carrier')))
						order_vals.update({'carrier_prestashop': self.create_carrier(self.get_value_data(carrier_data.get('carrier'))).id})
					except:
						pass

			sale_order_ids = sale_order_obj.search([('presta_id','=', self.get_value_data(order_detail.get('id')))])
			if not sale_order_ids:
				s_id = sale_order_obj.create(order_vals)
				logger.info('created orders ===> %s', s_id.id)
			else:
				s_id = sale_order_ids[0]

			if s_id:
				self.env.cr.execute("select saleorder_id from saleorder_shop_rel where saleorder_id = %s and shop_id = %s" % (s_id.id, self.id))
				so_data = self.env.cr.fetchone()
				if so_data == None:
					# print ("444444444444")
					self.env.cr.execute("insert into saleorder_shop_rel values(%s,%s)" % (s_id.id, self.id))

			self.manageOrderLines(s_id, order_detail, prestashop)
			self.manageOrderWorkflow(s_id, order_detail, st_id)
			self.env.cr.commit()
			return s_id
		except Exception as e:
			print('e------------------------------------------',e)
			print('e-------------------self.env.context-----------------------',self.env.context)
			if self.env.context.get('log_id'):
				log_id =  self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create({'all_operations':'import_orders','error_lines': [(0,0, {'log_description': str(e)})]})
				log_id = log_id_obj.id
			# self = self.with_context(log_id = log_id.id)
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
			print('self.env.context0000000---------------',self.env.context)
		return True



	# @api.multi
	def import_orders(self):
		print("=======import_orders>>>>>>>>")
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			ctx={}
			order_data= prestashop.get('orders')
			print("==order_data=>",order_data)
			if  order_data.get('orders') and order_data.get('orders').get('order'):
				orders =  order_data.get('orders').get('order')
				if isinstance(orders, list):
					orders = orders
				else:
					orders = [orders]
				for order in orders:
					order_vals = {}
					order_id =  self.get_value_data(order.get('attrs').get('id'))
					if order_id:
						order_detail = prestashop.get('orders', order_id)
						order_data_ids = order_detail.get('order')
						self.with_context(ctx).create_presta_order(order_data_ids, prestashop)
		shop.write({'last_prestashop_order_import_date': datetime.today()})
		self.env.cr.commit()
		return True


	# @api.multi
	def import_messages(self):
		print("inport message======")
		order_msg = self.env['order.message']
		res_obj = self.env['res.partner']
		sale_obj = self.env['sale.order']
		try:
			for shop in self:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				message = prestashop.get('customer_threads')
				if message.get('customer_threads') and message.get('customer_threads').get('customer_thread'):
					messages = message.get('customer_threads').get('customer_thread')
					if isinstance(messages, list):
						messages = messages
					else:
						messages = [messages]
					for msg_id in messages:
						thread_data = prestashop.get('customer_threads',self.get_value_data(msg_id.get('attrs').get('id')))
						order_msg_vals = {
							'msg_prest_id': self.get_value_data(thread_data.get('customer_thread').get('id')),
							'token': self.get_value_data(thread_data.get('customer_thread').get('token')),
							'email': self.get_value_data(thread_data.get('customer_thread').get('email')),
							'status': self.get_value_data(thread_data.get('customer_thread').get('status')),
						}
						if self.get_value_data(thread_data.get('customer_thread').get('id_customer')):
							p_ids = res_obj.search([('presta_id', '=', self.get_value_data(thread_data.get('customer_thread').get('id_customer')))])
							if p_ids:
								order_msg_vals.update({'customer_id': p_ids[0].id,})
							else:
								if self.get_value_data(thread_data.get('customer_thread').get('id_customer')) != '0' :
									customer_detail = prestashop.get('customers', self.get_value_data(thread_data.get('customer_thread').get('id_customer')))
									p_ids = self.create_customer(customer_detail,prestashop)
									order_msg_vals.update({'customer_id': p_ids[0].id,})
								elif self.get_value_data(thread_data.get('customer_thread').get('id_customer')) == '0' and self.get_value_data(thread_data.get('customer_thread').get('id_order')) == '0':
									continue
								elif self.get_value_data(thread_data.get('customer_thread').get('id_customer')) == '0' and self.get_value_data(thread_data.get('customer_thread').get('id_order')) != '0':
									p_ids = res_obj.search([('name', '=','Guest')])
									if p_ids:
										order_msg_vals.update({'customer_id': p_ids[0].id,})
						order_presta_id = self.get_value_data(thread_data.get('customer_thread').get('id_order'))
						if order_presta_id:
							order = sale_obj.search([('presta_id', '=', self.get_value_data(thread_data.get('customer_thread').get('id_order')))])
							if order:
								order_msg_vals.update({'new_id': order and order[0].id or False, })
							else:
								if self.get_value_data(thread_data.get('customer_thread').get('id_order')) != '0':
									order_detail = prestashop.get('orders', self.get_value_data(thread_data.get('customer_thread').get('id_order')))
									order_data_ids = order_detail.get('order')
									o_ids = self.create_presta_order(order_data_ids, prestashop)
									order_msg_vals.update({'new_id': o_ids[0].id})
						mmsg_ids = self.get_value_data(thread_data.get('customer_thread').get('id'))
						if isinstance(mmsg_ids, list):
							mmsg_ids = mmsg_ids
						else:
							mmsg_ids = [mmsg_ids]
						user_id = False
						print('--------',mmsg_ids)
						for mid in mmsg_ids:
							print('--------==========',prestashop.get('customer_messages'))
							msg_data = prestashop.get('customer_messages').get('customer_messages',mid)
							print('------------msg_data----',msg_data)
							if msg_data:
								value = self.get_value_data(msg_data.get('customer_message'))
								private = self.get_value_data(msg_data.get('customer_message'))
								for val in value :
									if val:
										order_msg_vals.update({'message':val.get('message')})
								if private:
									for val in private :
										if val:
											order_msg_vals.update({'private':val.get('private')})
								order_msg_vals.update({
									# 'message':value,
									# 'private': self.get_value_data(msg_data.get('customer_message').get('private')),
									'status': self.get_value_data(thread_data.get('customer_thread').get('status')),
									'presta_id': self.get_value_data(thread_data.get('customer_thread').get('id')),
								})
								id_employee = self.get_value_data(msg_data.get('customer_message'))
								for val in id_employee :
									if val:
										empl_id = val.get('id_employee')
								if empl_id:
									empl_data=prestashop.get('employees',empl_id)
									email_emp = self.get_value_data(empl_data.get('employee').get('email'))
									user_id = res_obj.search([('email','=',email_emp)])
									if not user_id:
										user_vals = {
											'name': self.get_value_data(empl_data.get('employee').get('firstname')),
											'email': self.get_value_data(empl_data.get('employee').get('email')),
										}
										user_id = res_obj.create(user_vals).id
									else:
										user_id = user_id[0].id
								order_msg_vals.update({'employee_id':user_id})
								order_msg_id = order_msg.search([('token','=',order_msg_vals.get('token')),('msg_prest_id','=',order_msg_vals.get('msg_prest_id'))])
								if not order_msg_id:
									msg_id = order_msg.create(order_msg_vals)
									logger.info('created messages ===> %s', msg_id.id)
									self.env.cr.commit()
								else:
									order_msg_id.write(order_msg_vals)
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'import_messages', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		self.write({'last_prestashop_msg_import_date': datetime.today()})
		return True


	# @api.multi
	def import_cart_rules(self):
		cart_obj = self.env['cart.rules']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				last_import_cart = shop.last_presta_cart_rule_import_date
				if last_import_cart:
					last_imported_cart = last_import_cart.date()
					cart = prestashop.get('cart_rules',options={'filter[date_upd]':last_imported_cart,'date':'1'})
				else:
					cart = prestashop.get('cart_rules')
					if cart.get('cart_rules') and cart.get('cart_rules').get('cart_rule'):
						carts = cart.get('cart_rules').get('cart_rule')
						if isinstance(carts, list):
							carts = carts
						else:
							carts = [carts]
						for each in carts:
							cart_id = self.get_value_data(each.get('attrs').get('id'))
							if cart_id :
								cart_data = prestashop.get('cart_rules',cart_id)
								id_customer = str(self.get_value_data(cart_data.get('cart_rule').get('id_customer')))
								partner_id = False
								if id_customer != '0':
									customer_data = prestashop.get('customers',id_customer)
									email = self.get_value_data(customer_data.get('customer').get('email'))
									res_obj = self.env['res.partner'].search([('email','=',email)])
									if res_obj:
										partner_id = res_obj[0].id
									else :
										partner_id = False
								cart_vals = {
									'id_customer':partner_id or False,
									'date_from': self.get_value_data(cart_data.get('cart_rule').get('date_from')),
									'date_to': self.get_value_data(cart_data.get('cart_rule').get('date_to')),
									'description': self.get_value_data(cart_data.get('cart_rule').get('description')),
									'quantity': self.get_value_data(cart_data.get('cart_rule').get('quantity')),
									'code': self.get_value_data(cart_data.get('cart_rule').get('code')),
									'partial_use':bool(int( self.get_value_data(cart_data.get('cart_rule').get('partial_use')))),
									'minimum_amount': self.get_value_data(cart_data.get('cart_rule').get('minimum_amount')),
									'free_shipping':bool(int( self.get_value_data(cart_data.get('cart_rule').get('free_shipping')))),
									# 'name' : cart_data.get('cart_rule').get('name').get('language').get('value'),
									'name' :self.get_value_data(self.get_value( cart_data.get('cart_rule').get('name').get('language'))),
									'presta_id' : cart_id,
								}
								carts_ids = cart_obj.search([('code', '=', self.get_value_data(cart_data.get('cart_rule').get('code')))])
								if not carts_ids:
									carts_id = cart_obj.create(cart_vals)

								else:
									carts_ids.write(cart_vals)
									carts_id = carts_ids[0]
								self.env.cr.execute("select cart_id from cart_shop_rel where cart_id = %s and shop_id = %s" % (carts_id.id, shop.id))
								data = self.env.cr.fetchone()
								if not data:
									self.env.cr.execute("insert into cart_shop_rel values(%s,%s)" % (carts_id.id, shop.id))
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'import_cart_rules', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'last_presta_cart_rule_import_date': datetime.now()})
			self.env.cr.commit()
			return True


	#import_cart_rules
	# @api.multi
	def import_catalog_price_rules(self):
		catalog_price_obj = self.env['catalog.price.rules']
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			try:
				last_import_catalog = shop.last_presta_catalog_rule_import_date
				if last_import_catalog:
# 					last_imported_catalog = ">["+last_import_catalog[:11]+"]"
					last_imported_catalog = last_import_catalog.date()
					catalog_rule = prestashop.get('specific_price_rules',options={'filter[date_upd]':last_imported_catalog,'date':'1'})
					print("catalog_rule====",catalog_rule)
				else:
					catalog_rule = prestashop.get('specific_price_rules',options={'filter[id_shop]':shop.presta_id,})
					print ("CATALOGGGGGGGGGGGGG",catalog_rule)
					if catalog_rule.get('specific_price_rules') and catalog_rule.get('specific_price_rules').get('specific_price_rule'):
						catalog_rules = catalog_rule.get('specific_price_rules').get('specific_price_rule')
						if isinstance(catalog_rules, list):
							catalog_rules = catalog_rules
						else:
							catalog_rules = [catalog_rules]
						for each in catalog_rules:
							catalog_id = self.get_value_data(each.get('attrs').get('id'))
							if catalog_id:
								catalog_data = prestashop.get('specific_price_rules', catalog_id)
								from_date = False
								if not self.get_value_data(catalog_data.get('specific_price_rule').get('from')) == '0000-00-00 00:00:00':
									from_date = self.get_value_data(catalog_data.get('specific_price_rule').get('from'))
								to_date = False
								if not self.get_value_data(catalog_data.get('specific_price_rule').get('to')) == '0000-00-00 00:00:00':
									to_date = self.get_value_data(catalog_data.get('specific_price_rule').get('to'))
								rule_vals = {
									'name': self.get_value_data(catalog_data.get('specific_price_rule').get('name')),
									'from_quantity': self.get_value_data(catalog_data.get('specific_price_rule').get('from_quantity')),
									'price': self.get_value_data(catalog_data.get('specific_price_rule').get('price')),
									'reduction': self.get_value_data(catalog_data.get('specific_price_rule').get('reduction')),
									'reduction_type': self.get_value_data(catalog_data.get('specific_price_rule').get('reduction_type')),
									'from_date': from_date,
									'to_date': to_date,
									'presta_id':catalog_id,
									# 'shop_ids': [(6, 0, shop.id)],
									# 'shop_ids' : catalog_data.get('specific_price_rule').get('id'),
								}
								rule_ids = catalog_price_obj.search([('name','=', self.get_value_data(catalog_data.get('specific_price_rule').get('name')))])
								if not rule_ids:
									rule_id = catalog_price_obj.create(rule_vals)
									logger.info('created catalog RULE ===> %s', rule_id.id)
								else:
									rule_ids.write(rule_vals)
									rule_id = rule_ids[0]
								self.env.cr.execute("select catalog_id from catalog_shop_rel where catalog_id = %s and shop_id = %s" % (rule_id.id, shop.id))
								data = self.env.cr.fetchone()
								if not data:
									self.env.cr.execute("insert into catalog_shop_rel values(%s,%s)" % (rule_id.id, shop.id))
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'import_catalog_rules', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
		shop.write({'last_presta_catalog_rule_import_date':datetime.now()})
		self.env.cr.commit()
		return True

	# @api.multi
	def update_prestashop_category(self):
		print ("==update_prestashop_categoryyyyyyyyy====>")
		categ_obj = self.env['prestashop.category']
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			try:
				query = "select categ_id from presta_categ_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_categ = self.env.cr.fetchall()
				if shop.prestashop_last_update_category_date:
					categ_ids = categ_obj.search([('write_date','>=', shop.prestashop_last_update_category_date),('id','in',fetch_categ)])
				else:
					categ_ids = categ_obj.search([('id','in',fetch_categ)])
				for each in categ_ids:
						d=each.presta_id.replace('[','')
						c=d.replace(']','')
						v=c.split()
						print("dd========",c,type(v))
						for i in v:
							if i.isdigit():
								k=i
						print("k====",k)
						cat = prestashop.get('categories',k)
						cat.get('category').update({
								'id': k,
								'name': {'language': {'attrs': {'id': '1'}, 'value': str(each.name)}},
								'active': 1,
								'id_parent': each.parent_id and str(each.parent_id.presta_id) or 0,
							})

						cat.get('category').pop('level_depth')
						cat.get('category').pop('nb_products_recursive')
						result = prestashop.edit('categories', cat)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create({'all_operations': 'update_categories', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'prestashop_last_update_category_date': datetime.now()})
		return True



	# @api.multi
	def update_cart_rules(self):
		print ("======update_cart_rules======")
		cart_obj = self.env['cart.rules']
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			try:
				query = "select cart_id from cart_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_cart_rules = self.env.cr.fetchall()
				if fetch_cart_rules != None:
					fetch_cart_rules = [i[0] for i in fetch_cart_rules]
					if shop.prestashop_last_update_cart_rule_date:
						cart_ids = cart_obj.search([('write_date', '>=', shop.prestashop_last_update_cart_rule_date),('id','in',fetch_cart_rules)])
					else:
						cart_ids = cart_obj.search([('id','in',fetch_cart_rules)])

					for each in cart_ids:
						# try:
							cart = prestashop.get('cart_rules', each.presta_id)
							cart.get('cart_rule').update(
								{
									'id':  each.presta_id and str(each.presta_id),
									'code': each.code and str(each.code),
									'description': each.description and str(each.description),
									'free_shipping': each.free_shipping and str(int(each.free_shipping)),
									'id_customer':  each.id_customer and each.id_customer.presta_id and str(each.id_customer.presta_id) or '0',
									'date_to': str(each.date_to) or  '0000-00-00 00:00:00',
									'name': {'language': {'attrs': {'id': '1'}, 'value': each.name and str(each.name)}},
									'date_from': str(each.date_from) or '0000-00-00 00:00:00',
									'partial_use': each.partial_use and str(int(each.partial_use)),
									'quantity': str(each.quantity),
								})
							prestashop.edit('cart_rules', cart)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create({'all_operations': 'update_cart_rules', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'prestashop_last_update_cart_rule_date': datetime.now()})
		return True

	# @api.multi
	def update_catalog_rules(self):
		print ("======update_catalog_rules======")
		catalog_price_obj = self.env['catalog.price.rules']
		for shop in self:
			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
			try:
				query = "select catalog_id from catalog_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_catalog_rules = self.env.cr.fetchall()
				if fetch_catalog_rules is not None:
					fetch_catalog_rules = [i[0] for i in fetch_catalog_rules]
					if shop.prestashop_last_update_catalog_rule_date:
						catalog_ids = catalog_price_obj.search([('write_date', '>', shop.prestashop_last_update_catalog_rule_date),('id', 'in', fetch_catalog_rules)])
					else:
						catalog_ids = catalog_price_obj.search([('id', 'in', fetch_catalog_rules)])
					for each in catalog_ids:
						catalog = prestashop.get('specific_price_rules', each.presta_id)
						catalog.get('specific_price_rule').update({
							'id':  str(each.presta_id),
							'reduction_type': str(each.reduction_type),
							'name': str(each.name),
							'price': str(each.price),
							'from_quantity': str(each.from_quantity),
							'reduction': str(each.reduction),
							'from': str(each.from_date)  or '0000-00-00 00:00:00',
							'to': str(each.to_date) or '0000-00-00 00:00:00',
							'id_shop':1,
							'id_country':0,
							'id_currency':0,
							'id_group':0,
							'reduction_tax':0
						})
						prestashop.edit('specific_price_rules', catalog)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create({'all_operations': 'update_catalog_rules', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'prestashop_last_update_catalog_rule_date': datetime.now()})
		return True

	# @api.multi
	def update_products(self,variant=False):
		print ("======update_products======")
		#update product details,image and variants
		prod_templ_obj = self.env['product.template']
		prdct_obj = self.env['product.product']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select product_id from product_templ_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_products = self.env.cr.fetchall()
				if fetch_products is not None:
					fetch_products = [i[0] for i in fetch_products]
					if shop.prestashop_last_update_product_data_date:
						product_data_ids = prod_templ_obj.search([('write_date', '>=',shop.prestashop_last_update_product_data_date),('id', 'in',fetch_products)])
					else:
						product_data_ids = prod_templ_obj.search([('id', 'in',fetch_products)])

					for each in product_data_ids:
						product = prestashop.get('products', each.presta_id)
						categ = [{'id': each.presta_categ_id.presta_id and str(each.presta_categ_id.presta_id)}]
						parent_id = each.presta_categ_id.parent_id
						while parent_id:
							categ.append({'id': parent_id.presta_id and str(parent_id.presta_id)})
							parent_id = parent_id.parent_id
						product.get('product').get('associations').update({'categories': {'attrs': {'node_type': 'category'}, 'category': categ},})
						product.get('product').update({
							'name': {'language': {'attrs': {'id': '1'}, 'value': each.name and str(each.name)}},
							'active': '1',
							'type': 'simple',
							'on_sale':'1',
							'state': '1',
							'online_only': '1',
							'reference': each.default_code and str(each.default_code),
							'wholesale_price': each.wholesale_price and str(each.wholesale_price),
							'price': each.list_price and str(each.list_price),
							'depth': each.product_lngth and str(each.product_lngth),
							'width': each.product_width and str(each.product_width),
							'weight': each.product_wght and str(each.product_wght),
							'height': each.product_hght and str(each.product_hght),
							'available_now': ({'language': {'attrs': {'id': '1'}, 'value': each.product_instock and str(int(each.product_instock))}}),
							'on_sale' : each.product_onsale and str(int(each.product_onsale)) ,
							'id':  each.presta_id and str(each.presta_id),
							'id_supplier': each.supplier_id and str(each.supplier_id.presta_id) or '0',
							'id_manufacturer': each.manufacturer_id and str(each.manufacturer_id.presta_id) or '0',
							'id_category_default':each.presta_categ_id and str(each.presta_categ_id.presta_id),
							'position_in_category':'',
							# 'description': {'language': {'attrs': {'id': '1'}, 'value': each.product_description}}
							# 'name': {'language': {'attrs': {'id': '1'}, 'value': each.prd_label}},
							# 'product_img_ids':product.get('associations').get('images').get('image') or False,
						})
						product.get('product').pop('quantity')
						combination_list = []
						if each.attribute_line_ids:
							prod_variant_ids = prdct_obj.search([('product_tmpl_id', '=', each.id)])
							for variant in prod_variant_ids:
								if variant.combination_id:
									prod_variants_comb = prestashop.get('combinations', variant.combination_id)
									option_values = []
									for op in variant.product_template_attribute_value_ids:
										option_values.append({'id': op.presta_id and str(op.presta_id)})
									prod_variants_comb.get('combination').get('associations').get('product_option_values').update({
										'product_option_value' : option_values[0]
									})
	#
									prod_variants_comb.get('combination').update({
										'is_virtual':'1',
										'id_product': variant.product_tmpl_id and str(variant.product_tmpl_id.presta_id),
										'reference': variant.default_code and str(variant.default_code),
										'id': variant.combination_id and str(variant.combination_id),
										'minimal_quantity': '1',
										'price': variant.prdct_unit_price and str(variant.prdct_unit_price),
									})
									response_comb = prestashop.edit('combinations', prod_variants_comb)
									combination_list.append({'id':  variant.combination_id})
						if combination_list:
							product.get('product').get('associations').get('combinations').update({
											'combination' : combination_list
								})
						product.get('product').pop('manufacturer_name')
						response = prestashop.edit('products', product)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'update_product_data', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'prestashop_last_update_product_data_date': datetime.now()})
		return True

# 	@api.multi
# 	def update_product_price(self):
# 		print ("======update_product_price======")
# 		# update product price
# 		prod_templ_obj = self.env['product.template']
# 		prdct_obj = self.env['product.product']
# 		stock_quant_obj = self.env['stock.quant']
#
# 		for shop in self:
# 			prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,
# 												  shop.prestashop_instance_id.webservice_key,physical_url = shop.shop_physical_url or None)
# #             try:
# 			query = "select product_id from product_templ_shop_rel where shop_id = %s"%shop.id
# 			self.env.cr.execute(query)
# 			fetch_products_price = self.env.cr.fetchall()
# 			if fetch_products_price != None:
# 				fetch_products_price = [i[0] for i in fetch_products_price]
# 				# if shop.prestashop_last_update_product_data_date:
# 				#     product_data_ids = prod_templ_obj.search(
# 				#         [('write_date', '>=', shop.prestashop_last_update_product_data_date),('id', 'in',fetch_products_price)])
# 				#     print ("=====product_data_ids111111======",product_data_ids)
# 				# else:
# 				product_data_ids = prod_templ_obj.search([('id', 'in',fetch_products_price)])
# 				for each in product_data_ids:
# 							# print ("EACHHHHHHHHH",each)
# #                             try:
# 							product = prestashop.get('products', each.presta_id)
# 							# print ("PRODUCTTTTTTTTTT",product)
# 							categ = [{'id': each.presta_categ_id.presta_id}]
# 							parent_id = each.presta_categ_id.parent_id
# 							while parent_id:
# 								categ.append({'id': parent_id.presta_id})
# 								parent_id = parent_id.parent_id
# 							product.get('product').get('associations').update({
# 								'categories': {'attrs': {'node_type': 'category'}, 'category': categ},
# 							})
#
# 							product.get('product').update({
# 								# 'price': str(each.prdct_unit_price),
# 								'price': str(each.with_context(pricelist=self.pricelist_id.id).price),
# #                                 'quantity':0,
# 								'wholesale_price': each.wholesale_price and str(each.wholesale_price),
# 								'id': each.presta_id and str(each.presta_id),
# 								'position_in_category':'',
# 								'id_category_default':each.presta_categ_id and str(each.presta_categ_id) and each.presta_categ_id.presta_id,
# 								# 'available_now': (
# 								# {'language': {'attrs': {'id': '1'}, 'value': str(int(each.product_instock))}}),
# 								# 'on_sale': str(int(each.product_onsale)),
# 								# 'id': each.presta_id,
# 							})
#
# 							if each.attribute_line_ids:
# 								# try:
# 								prod_variant_ids = prdct_obj.search([('product_tmpl_id', '=', each.id)])
# 									# if not prod_variant_ids:
#
# 								for variant in prod_variant_ids:
# 										if variant.combination_id:
# 											print("=======prod_variant_ids========>",prod_variant_ids)
# 											print("=======prestashop.get('combinations'========>",prestashop.get('combinations'))
# 											prod_variants_comb = prestashop.get('combinations', variant.combination_id)
# 											print("=======prod_variants_comb========>",prod_variants_comb)
# 											# prod_variants_comb_price = prestashop.get('combinations', variant.combination_price)
# 											# print "prod_variants_comb_price===>",prod_variants_comb_price
# #                                             option_values = []
# #                                             for op in variant.attribute_value_ids:
# #                                                 option_values.append({'id': op.presta_id})
# #                                             prod_variants_comb.get('combination').get('associations').get('product_option_values').update({
# #                                                 'product_option_value' : option_values
# #                                             })
# 											prod_variants_comb.get('combination').update({
# 												# 'id_product': variant.product_tmpl_id.presta_id,
# 												# 'reference': variant.default_code,
# 												'minimal_quantity': '1',
# #                                                 'position_in_category':'',
# 												# 'price': str(variant.prdct_unit_price),
# 												# 'id': variant.combination_id and str(variant.combination_id),
# 												# 'id_product': variant.product_tmpl_id and str(variant.product_tmpl_id.presta_id),
# 												'id_product': variant.product_tmpl_id and variant.product_tmpl_id.presta_id and str(variant.product_tmpl_id.presta_id),
# 												'price': str(variant.with_context(pricelist=self.pricelist_id.id).price),
# 												'wholesale_price': variant.wholesale_price and str(variant.wholesale_price),
# 											})
# 											prod_variants_comb.get('combination').pop('quantity')
# 											# print("==========result=======>",result)
# 											prestashop.edit('combinations', prod_variants_comb)
# 								# except:
# 								#     pass
# #
# 							product.get('product').pop('manufacturer_name')
# 							product.get('product').pop('quantity')
# 							prestashop.edit('products', product)
# #                             except Exception as e:
# #                                 if self.env.context.get('log_id'):
# #                                     log_id = self.env.context.get('log_id')
# #                                     self.env['log.error'].create(
# #                                         {'log_description': str(e) + ' While updating product price %s' % (each.name),
# #                                          'log_id': log_id})
# #                                 else:
# #                                     log_id = self.env['prestashop.log'].create({'all_operations': 'update_product_price',
# #                                                                                 'error_lines': [(0, 0, {'log_description': str(
# #                                                                                     e) + ' While updating product price %s' % (
# #                                                                                 each.name)})]})
# #                                     self = self.with_context(log_id=log_id.id)
#
# #             except Exception as e:
# #                 if self.env.context.get('log_id'):
# #                     log_id = self.env.context.get('log_id')
# #                     self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
# #                 else:
# #                     log_id = self.env['prestashop.log'].create(
# #                         {'all_operations': 'update_product_price', 'error_lines': [(0, 0, {'log_description': str(e)})]})
# #                     self = self.with_context(log_id=log_id.id)
# 		shop.write({'prestashop_last_update_product_data_date': datetime.now()})
# 		return True

	# @api.multi
	def update_presta_product_inventory(self):
		print ("======update_presta_product_inventory======")

		prod_templ_obj = self.env['product.template']
		prdct_obj = self.env['product.product']
		stck_quant = self.env['stock.quant']
		try:
			for shop in self:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
	#             try:
				if self.env.context.get('product_ids'):
					p_ids = prod_templ_obj.browse(self.env.context.get('product_ids'))
				elif shop.prestashop_last_update_product_data_date:
						stck_ids = stck_quant.search([('write_date', '>', shop.prestashop_last_update_product_data_date)])
						p_ids = []
						for i in stck_ids:
							if i.product_id not in p_ids:
								p_ids.append(i.product_id)
				else:
					p_ids = prdct_obj.search([('presta_id', '!=',False)])
					print ("======p_idsp_ids======",p_ids)
				for each in p_ids:
					if each.presta_inventory_id:
						prod_variant_inventory = prestashop.get('stock_availables', each.presta_inventory_id)
						query = "SELECT sum(quantity) FROM stock_quant where product_id = %s and location_id = %s group by product_id"%(each.id, shop.warehouse_id.lot_stock_id.id)
						self.env.cr.execute(query)
						qty = self.env.cr.fetchone()
						if qty:
							if not each.combination_id:
								prod_variant_inventory.get('stock_available').update({
								'quantity': str(int(qty[0])),
								'id': each.presta_inventory_id and str(each.presta_inventory_id),
								'id_product': each.product_tmpl_id.presta_id,
								'id_product_attribute':'0',
								'depends_on_stock':0,
								'out_of_stock':2,
								'id_shop': shop.presta_id and str(shop.presta_id)
							})
							else :
								prod_variant_inventory.get('stock_available').update({
								'quantity': str(int(qty[0])),
								'id': each.presta_inventory_id and str(each.presta_inventory_id),
								'id_product': each.product_tmpl_id.presta_id ,
								'id_product_attribute': each.combination_id and str(each.combination_id),
								'depends_on_stock':0,
								'out_of_stock':2,
								'id_shop': shop.presta_id and str(shop.presta_id)
							})
							print ("======afterupdate======",prod_variant_inventory.get('stock_available'))
						r = prestashop.edit('stock_availables', prod_variant_inventory)
		except Exception as e:
			if self.env.context.get('log_id'):
				log_id = self.env.context.get('log_id')
				self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
			else:
				log_id_obj = self.env['prestashop.log'].create(
					{'all_operations': 'update_inventory', 'error_lines': [(0, 0, {'log_description': str(e), })]})
				log_id = log_id_obj.id
			new_context = dict(self.env.context)
			new_context.update({'log_id': log_id})
			self.env.context = new_context
		shop.write({'prestashop_last_update_product_data_date': datetime.now()})


	# @api.multi
	def update_order_status(self):
		print ("=====update_order_status====")
		sale_order = self.env['sale.order']
		status_obj = self.env['presta.order.status']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select * from sale_order o, presta_order_status ps  where o.presta_id is not null and ps.name in ('Awaiting check payment','Awaiting bank wire payment','Awaiting Cash On Delivery validation','Processing in progress') and shop_id = %s"%(shop.id)
				self.env.cr.execute(query)
				fetch_orders = self.env.cr.fetchall()
				if fetch_orders is not None:
					fetch_orders = [i[0] for i in fetch_orders]
					if shop.prestashop_last_update_order_status_date:
						sale_order_ids = sale_order.search([('id', 'in',fetch_orders),('order_status.name','in',['Awaiting check payment','Awaiting bank wire payment','Awaiting Cash On Delivery validation','Processing in progress'])])
					else:
						sale_order_ids = sale_order.search([('id', 'in',fetch_orders)])
					#import order status
					order_states = prestashop.get('order_states')
					os_status = order_states.get('order_states').get('order_state')
					if isinstance(os_status, list):
						os_status = os_status
					else:
						os_status = [os_status]
					for status in os_status:
						state_ids = status_obj.search([('presta_id', '=', status.get('attrs').get('id'))])
						if state_ids:
							st_id = state_ids[0]
						else:
							orders_status_lst = prestashop.get('order_states',  status.get('attrs').get('id'))
							st_id = status_obj.create(
								{'name': self.get_value(orders_status_lst.get('order_state').get('name').get('language')).get('value'),
								 'presta_id': orders_status_lst.get('order_state').get('id')})
					for sale_order in sale_order_ids:
						order = prestashop.get('orders', sale_order.presta_id)
						order.get('order').update({
													'reference': sale_order.presta_order_ref and str(sale_order.presta_order_ref),
													# 'conversion_rate': '1.000000',
													'module': str(sale_order.pretsa_payment_mode),
													'id_customer':1,
													'id_address_delivery':1,
													'id_address_invoice' :1,
													'id_cart':1,
													'id_currency':1,
													'total_products': str(sale_order.amount_total),
													'id_carrier': sale_order.carrier_prestashop and str(sale_order.carrier_prestashop.presta_id),
													'payment': {'bankwire': 'Bankwire'},
													'id': sale_order and str(sale_order.presta_id),
													'id_lang':1,
													'total_paid':sale_order.amount_untaxed and str(sale_order.amount_untaxed),
													'total_paid_real':sale_order.amount_total and str(sale_order.amount_total),
													'total_products_wt': 1,
													'conversion_rate': 1
													# 'id_shop': '1',
						})
						if sale_order.invoice_status == 'invoiced':

							order.get('order').get('total_paid_tax_incl').update({'value': str(sale_order.amount_total)})
							order.get('order').get('total_paid_tax_excl').update({'value': str(sale_order.amount_untaxed)})

						shipping_product = shop.shipment_fee_product_id
						for line in sale_order.order_line:
							if line.product_id.id == shipping_product.id:
								shipping_cost = shipping_product.lst_price

								order.get('order').update({'total_shipping': str(shipping_cost)})
								order.get('order').update({'total_shipping_tax_excl': str(shipping_cost)})
						discount = 0.0
						for line in sale_order.order_line:
							discount += line.discount
						if discount>0.0:
							order.get('order').update({'total_discounts':discount})
							order.get('order').update({'total_discounts_tax_excl':discount})

						if sale_order.order_status.name in ['Awaiting check payment','Awaiting bank wire payment','Awaiting Cash On Delivery validation','Processing in progress']:
							# print "inside iffffffff"
							invoice_not_done = False
							for invoice in sale_order.invoice_ids:
								if invoice.state == 'open' or invoice.state == "paid" :
									order.get('order').update({'invoice_number': str(invoice.number)})
									order.get('order').update({'invoice_date': str(invoice.date_invoice)})
									order.get('order').update({'total_paid_real': str(sale_order.amount_total)})
									# order.get('order').update({'current_state': str(status_ids[0].presta_id)})
								else:
									invoice_not_done = True
							if invoice_not_done == False:
								# sddddd
								status_ids = status_obj.search([('name','=','Payment accepted')])
								order.get('order').update({'current_state': str(status_ids[0].presta_id)})
								sale_order.order_status = status_ids[0].id

							picking_not_done = False
							for picking in sale_order.picking_ids:
								status_ids = status_obj.search([('name', '=', 'Shipped')])
								if picking.state == 'done':
									order.get('order').update({'delivery_number': str(picking.name)})
									order.get('order').update({'delivery_date': picking.scheduled_date})
									order.get('order').update({'current_state': str(status_ids[0].presta_id)})
								else:
									picking_not_done = True

							if picking_not_done == False:
								status_ids = status_obj.search([('name', '=', 'Shipped')])
								order.get('order').update({'current_state': str(status_ids[0].presta_id)})
								sale_order.order_status = status_ids[0].id
						prestashop.edit('orders', order)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'update_order_status', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
			shop.write({'prestashop_last_update_order_status_date': datetime.now()})
		return True


	# @api.multi
	def export_presta_products(self):
		print ("====export_presta_products====")
		# exports product details,image and variants
		prod_templ_obj = self.env['product.template']
		prdct_obj = self.env['product.product']
		stock_quanty = self.env['stock.quant']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select product_id from product_templ_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_shop_products = self.env.cr.fetchall()
				if self.env.context.get('product_ids'):
					product_ids = prod_templ_obj.browse(self.env.context.get('product_ids'))
				else:
					product_ids = prod_templ_obj.search([('product_to_be_exported','=',True)])
				for product in product_ids:
					product_schema = prestashop.get('products', options={'schema': 'blank'})
					print ("product_schema before export====>",product_schema)
					print ("product.categ_id.presta_id===>",product.presta_categ_id)
					categ = [{'id': product.presta_categ_id.presta_id}]
					parent_id = product.presta_categ_id.parent_id
					print ("parent idssssssssssss",parent_id)
					while parent_id:
						categ.append({'id': parent_id.presta_id})
						parent_id = parent_id.parent_id
						print ("parrrrrrrr",parent_id)
						product_schema.get('product').get('associations').update({
							'categories': {'attrs': {'node_type': 'category'}, 'category': categ},
						})

					product_schema.get('product').update({
						'name': {'language': {'attrs': {'id': '1'}, 'value': product.name}},
						'link_rewrite': {'language': {'attrs': {'id': '1'}, 'value': product.name.replace(' ', '-')}},
						'reference': product.default_code,
						'wholesale_price': str(product.wholesale_price),
						'depth': str(product.product_lngth),
						'width': str(product.product_width),
						'weight': str(product.product_wght),
						'height': str(product.product_hght),
						'price': product.list_price and str(product.list_price) or '0.00',
						'date_upd': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'date_add': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'active': 1,
	# 					'state': {'value': '1'},
						'type': {'attrs': {'notFilterable': 'true'}, 'value': 'simple'},
						'id_supplier': product.supplier_id and product.supplier_id.presta_id or '0',
						'id_manufacturer': product.manufacturer_id and product.manufacturer_id.presta_id or '0',
						'id_shop_default':self.id
					})
					p_ids = prdct_obj.search([('product_tmpl_id', '=' ,product[0].id)])
					product_var_ids = prdct_obj.search([('product_tmpl_id','=',product.id)])
					print("product_var_idsproduct_var_ids",product_var_ids)

					print("product after update====>", product_schema)
					presta_res = prestashop.add('products', product_schema)
					presta_id = self.get_value_data(presta_res.get('prestashop').get('product').get('id'))
					product.write({'presta_id': presta_id})
					for prod_var in product_var_ids:
						stck_id = stock_quanty.search([('product_id','=',prod_var.id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
						qty = 0
						for stck in stck_id:
							qty += stck.quantity
						product_comb_schema = prestashop.get('combinations',options = {'schema': 'blank'})
						option_values = []
						for op in prod_var.product_template_attribute_value_ids:
							option_values.append({'id': op.presta_id})
						product_comb_schema.get('combination').get('associations').get('product_option_values').update({
							'product_option_value' : option_values
						})
						product_comb_schema.get('combination').update({
								'id_product' : presta_id,
								'price' : prod_var.combination_price and str(prod_var.combination_price) or '0.00',
								'reference': prod_var.default_code,
								'quantity': str(int(prod_var.qty_available)),
								'minimal_quantity': '1',
						})
						combination_resp = prestashop.add('combinations', product_comb_schema)
						c_presta_id = self.get_value_data(combination_resp.get('prestashop').get('combination').get('id'))
						prod_var.write({
							'combination_id': c_presta_id,
						})
					product.write({
						'product_to_be_exported': False,
					})
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'export_product_data', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
		return True


	# @api.multi
	def export_presta_categories(self):
		print ("====export_presta_categories====")
		categ_obj = self.env['prestashop.category']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select categ_id from presta_categ_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_shop_category = self.env.cr.fetchall()
				prestashop.category = categ_obj.search([])
				if self.env.context.get('category_ids'):
					category_ids = categ_obj.browse(self.env.context.get('category_ids'))
				else:
					category_ids = categ_obj.search([('to_be_exported','=',True),('id','in',fetch_shop_category)])
				for category in category_ids:
					category_schema = prestashop.get('categories', options={'schema': 'blank'})
					category_schema.get('category').update({
						'name' : {'language': {'attrs': {'id': '1'}, 'value': category.name and str(category.name)}} ,
						'id_parent': category.parent_id and category.parent_id.presta_id and str(category.parent_id.presta_id) or '0',
						'link_rewrite': {'language': {'attrs': {'id': '1'}, 'value':  category.name and str(category.name.replace(' ','-'))}},
						'active': '1',
						'description': {'language': {'attrs': {'id': '1'}, 'value': category.name and str(category.name)}},
						'id_shop_default':self.id,
						})
					presta_res = prestashop.add('categories', category_schema)
					if presta_res.get('prestashop').get('category').get('id'):
						categ_presta_id = self.get_value_data(presta_res.get('prestashop').get('category').get('id'))
					else:
						categ_presta_id = self.get_value_data(presta_res.get('prestashop').get('id'))
					category.write({
						'presta_id': categ_presta_id,
						'to_be_exported': False,
					})
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'export_categories', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context
		return True

	# @api.one
	def search_state(self, prestashop, state_name,country_id):
		print ("===state_name======>",state_name, state_name.name)
		# To find the country id in prestashop
		state_obj = self.env['res.country.state']
		state_ids = prestashop.search('states', options={'filter[name]': state_name.name})
		if state_ids:
			state_id = state_ids[0]
		else:
			stats_schema = prestashop.get('states', options={'schema': 'blank'})
			if stats_schema:
				print('stats_schema------',stats_schema)
				print('stats_schema------',stats_schema.get('state'))
				stats_schema.get('state').update({
					'name': state_name.name,
					'iso_code': state_name.code,
					'id_country': country_id,
				})
				stat_res = prestashop.add('states', stats_schema)
				state_id = stat_res.get('prestashop').get('state').get('id').get('value')
		return state_id

	# @api.one
	def search_country(self, prestashop, country_name):
		# To find the country id in prestashop
		country_ids = prestashop.search('countries', options={'filter[name]': country_name.name})
		if country_ids:
			country_id = country_ids[0]
		else:
			country_schema = prestashop.get('countries', options={'schema': 'blank'})
			country_schema.get('country').update({
				'name': {'language': {'attrs': {'id': '1'}, 'value': country_name.name}},
				'iso_code': country_name.code,
				'alias': ''
			})
			country_res = prestashop.add('countries', country_schema)
			country_id = country_res.get('prestashop').get('country').get('id').get('value')
		return country_id


	# @api.multi
	def export_presta_customers(self):
		print ("=====export_presta_customers===")
		res_partner_obj = self.env['res.partner']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select cust_id from customer_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_shop_customers = self.env.cr.fetchall()
				if self.env.context.get('customer_ids'):
					customer_ids = res_partner_obj.browse(self.env.context.get('customer_ids'))
				else:
					customer_ids = res_partner_obj.search([('to_be_exported', '=', True)])
		# 				('id','in',fetch_shop_customers)
				for customer in customer_ids:
					customer_schema = prestashop.get('customers', options={'schema': 'blank'})
					customer_name = customer.name
					name_list = customer_name.split(' ')
					first_name = name_list[0]
					if len(name_list) > 1:
						last_name = name_list[1]
					else:
						last_name = name_list[0]
					dob = customer.date_of_birth

					customer_schema.get('customer').update({
						'firstname' : first_name and str(first_name),
						'lastname' : last_name and str(last_name),
						'email' : customer.email and str(customer.email),
						'active': '1',
						'date_upd': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'date_add': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'birthday': customer.date_of_birth and str(customer.date_of_birth) or False,
						'website': customer.website and str(customer.website) or '' or False,
					})
					presta_cust = prestashop.add('customers', customer_schema)
					customer_presta_id = self.get_value_data(presta_cust.get('prestashop').get('customer').get('id'))
					address_schema = prestashop.get('addresses', options={'schema': 'blank'})
					address_schema.get('address').update({
						'firstname': first_name and str(first_name),
						'lastname': last_name and str(last_name),
						'address1' : customer.street and str(customer.street) or '',
						'address2' : customer.street2 and str(customer.street2) or '',
						'city' : customer.city and str(customer.city) or '',
						'phone' : customer.phone and str(customer.phone) or '',
						'phone_mobile' : customer.mobile and str(customer.mobile) or '',
						'postcode' : customer.zip and str(customer.zip) or '',
						'id_customer':  customer_presta_id and str(customer_presta_id),
						'alias': customer.type and str(customer.type),
					})
					if customer.country_id:
						c_id = shop.search_country(prestashop, customer.country_id)
						print('--------',c_id)
						if c_id:
							address_schema.get('address').update({
								'id_country': c_id,
							})
							# if customer.state_id:
							# 	address_schema.get('address').update({
							# 		'id_state': shop.search_state(prestashop, customer.state_id,c_id)
							# 	})


					presta_address = prestashop.add('addresses', address_schema)
					add_presta_id = self.get_value_data(presta_address.get('prestashop').get('address').get('id'))
					customer.write({
						'presta_id': customer_presta_id,
						'to_be_exported': False,
						'address_id' : add_presta_id,
					})
					for child in customer.child_ids:
						address_schema = prestashop.get('addresses', options={'schema': 'blank'})
						if child.name:
							name = child.name
						else:
							name = customer.name
						name_list = name.split(' ')
						first_name = name_list[0]
						if len(name_list) > 1:
							last_name = name_list[1]
						else:
							last_name = name_list[0]
						address_schema.get('address').update({
							'firstname': first_name and str(first_name),
							'lastname': last_name and str(last_name),
							'address1': child.street and str(child.street)  or '',
							'address2': child.streets and str(child.street2)  or '',
							'city': child.city and (child.city) or '',
							'phone': child.phone and str(child.phone) or '',
							'phone_mobile': child.mobile and str(child.mobile) or '',
							'postcode': child.zip and str(child.zip)  or '',
							'id_customer': customer_presta_id and str(customer_presta_id),
							'alias': customer.type and str(customer.type) or ''
						})
						if customer.state_id:
							address_schema.get('address').update({
								'id_state': shop.search_state(prestashop, child.state_id)
							})
						if customer.country_id:
							c_id = shop.search_country(prestashop, child.country_id)
							address_schema.get('address').update({
								'id_country': c_id[0],
							})
						presta_address = prestashop.add('addresses', address_schema)
						add_presta_id = self.get_value_data(presta_address.get('prestashop').get('address').get('id'))
						print('add_presta_id-------------',add_presta_id)
						child.write({
							'address_id': add_presta_id,
							'to_be_exported':False
						})
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'Export_customers', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context


	# @api.multi
	def export_presta_customer_messages(self):
		print("=====export_presta_customer_messages======",self.env.context)
		order_msg_obj = self.env['order.message']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select mess_id from message_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_shop_customer_messages = self.env.cr.fetchall()
				if self.env.context.get('customer_message_ids'):
					customer_message_ids = order_msg_obj.browse(self.env.context.get('customer_message_ids'))
				else:
					customer_message_ids = order_msg_obj.search([('to_be_exported', '=', True)])

				for customer_message in customer_message_ids:
					customer_message_schema = prestashop.get('customer_threads', options={'schema': 'blank'})
					customer_message_schema.get('customer_thread').update({
						'token': customer_message.token and str(customer_message.token),
						'email':  customer_message.email and str(customer_message.email) ,
						'status': customer_message.status and str(customer_message.status),
						'id_lang': '1',
						'id_customer' : customer_message.customer_id and str(customer_message.customer_id.presta_id) or '0',
						'id_contact': 0,
						'id_order':customer_message.new_id and str(customer_message.new_id.presta_id) or '',
					})
					customer_threads_res = prestashop.add('customer_threads', customer_message_schema)
					msg_presta_id = self.get_value_data(customer_threads_res.get('prestashop').get('customer_thread').get('id'))[0]
					customer_message.write({
						'presta_id': msg_presta_id,
						'to_be_exported': False,
					})
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'export_customer_message', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context

	# @api.one
	def get_currency(self, prestashop, currency):
		print("================currencycurrencycurrency==>>>>>>>>>>>>>",currency)
		currency_ids = prestashop.search('currencies', options={'filter[iso_code]': currency.name})
		if currency_ids:
			currency_id = currency_ids[0]
		else:
			currency_schema = prestashop.get('currencies', options={'schema': 'blank'})
			currency_schema.get('currency').update({
				'name': currency.name,
				'iso_code': currency.name,
				'sign': currency.name,
				'active': '1',
				'conversion_rate': '1'
			})
			currency_res = prestashop.add('currencies', currency_schema)
			currency_id = currency_res.get('prestashop').get('currency').get('id').get('value')
		return currency_id

	# @api.one
	def get_languange(self, prestashop, languange):
		lang = self.env['res.lang'].search([('code','=',languange)])
		languange_ids = prestashop.search('languages', options={'filter[iso_code]':  lang.iso_code})
		if languange_ids:
			languange_id = languange_ids[0]
		else:
			languange_schema = prestashop.get('languages', options={'schema': 'blank'})
			languange_schema.get('language').update({
				'name': lang.name,
				'iso_code': lang.iso_code,
				'language_code' : lang.code.replace('_','-'),
				'active': '1',
				'date_format_lite': lang.date_format,
			})
			languange_res = prestashop.add('languages', languange_schema)
			languange_id = self.get_value(languange_res.get('prestashop').get('language'))[0].get('id').get('value')
		return languange_id


	# @api.multi
	def export_presta_orders(self):
		print ("======export_presta_orders======")
		sale_order_obj = self.env['sale.order']
		status_obj = self.env['presta.order.status']
		sale_order_line_obj = self.env['sale.order.line']
		for shop in self:
			try:
				prestashop = PrestaShopWebServiceDict(shop.prestashop_instance_id.location,shop.prestashop_instance_id.webservice_key or None)
				query = "select saleorder_id from saleorder_shop_rel where shop_id = %s"%shop.id
				self.env.cr.execute(query)
				fetch_shop_sale_order = self.env.cr.fetchall()
				if self.env.context.get('ordered_ids'):
					order_ids = sale_order_obj.browse(self.env.context.get('ordered_ids'))
				else:
					order_ids = sale_order_obj.search([('to_be_exported', '=', True)])
				for order in order_ids:
					print('order_ids--------',order_ids)
					order_schema = prestashop.get('orders', options={'schema': 'blank'})
					carts_schema = prestashop.get('carts', options={'schema': 'blank'})
					# lang_schema = prestashop.get('languages',1)
					print ("order_schemaorder_schema",order_schema)
					payment_value = dict(self.env['sale.order'].fields_get(allfields=['pretsa_payment_mode'])['pretsa_payment_mode']['selection'])[order.pretsa_payment_mode]
					carts_schema = prestashop.get('carts', options={'schema': 'blank'})
					order_schema.get('order').update({
						'allow_seperated_package': '',
						'conversion_rate': '1.000000' ,
						'current_state':  order.order_status and order.order_status.presta_id and str(order.order_status.presta_id),
						'carrier_tax_rate': '0.000',
						'date_upd': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'date_add': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'delivery_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'delivery_number': '0',
						'id_shop': shop.presta_id and str(shop.presta_id),
						'id_customer': order.partner_id and order.partner_id.presta_id and str(order.partner_id.presta_id),
						'id_address_delivery': order.partner_id.address_id and str(order.partner_id.address_id),
						'id_address_invoice': order.partner_invoice_id.address_id and str(order.partner_invoice_id.address_id),
						'id_currency': shop.get_currency(prestashop, shop.pricelist_id.currency_id),
						'id_carrier': order.carrier_prestashop.presta_id and str(order.carrier_prestashop.presta_id),
						'invoice_number': '0',
						'id_lang': shop.get_languange(prestashop, order.partner_id.lang),
						# 'id_shop_group': '1',
						'mobile_theme': '0',
						'module': order.pretsa_payment_mode.lower(),
						'payment': order.pretsa_payment_mode.capitalize(),
						'round_mode': '0',
						'round_type': '0',
						'reference': order.name and str(order.name),
						'recyclable': '0',
						'shipping_number': {'attrs': {'notFilterable': 'true'}, 'value': ''},
						'total_paid': '0.000000',
						'total_paid_real': '0.000000',
						'total_products': order.amount_total and str(order.amount_total),
						'total_products_wt': '1.0' or '',
						'total_discounts' : '0.000000',
						'total_discounts_tax_excl' : '0.000000',
						'total_discounts_tax_incl' : '0.000000',
						'total_paid_tax_excl' : '0.000000',
						'total_paid_tax_incl' : '0.000000',
						'total_shipping' : '0.000000',
						'total_shipping_tax_excl' : '0.000000',
						'total_shipping_tax_incl' : '0.000000',
						'total_wrapping_tax_excl' : '0.000000',
						'total_wrapping_tax_incl' : '0.000000',
						'total_wrapping' : '0.000000',
						'valid': '1',
					})
					if order.invoice_status == 'invoiced':
						order_schema.get('order').update({'total_paid_tax_incl': order.amount_total and str(order.amount_total)})
						order_schema.get('order').update({'total_paid_tax_excl': order.amount_untaxed and str(order.amount_untaxed)})

					shipping_product = shop.shipment_fee_product_id
					for line in order.order_line:
						if line.product_id.id == shipping_product.id:
							shipping_cost = shipping_product.lst_price and str(shipping_product.lst_price)
							order_schema.get('order').update({'total_shipping': shipping_cost and str(shipping_cost)})
							order_schema.get('order').update({'total_shipping_tax_excl': shipping_cost and str(shipping_cost)})
					discount = 0.0
					status_ids=False
					for line in order.order_line:
						discount += line.discount
					if discount > 0.0:
						order_schema.get('order').update({'total_discounts': discount and str(discount)})
						order_schema.get('order').update({'total_discounts_tax_excl': discount and str(discount)})

					if order.order_status.name in ['Awaiting check payment', 'Awaiting bank wire payment',
														'Awaiting Cash On Delivery validation', 'Processing in progress']:
						invoice_not_done = False
						for invoice in order.invoice_ids:
							if invoice.state == 'open' or invoice.state == "paid":
								order_schema.get('order').update({'invoice_number': invoice.number and str(invoice.number)})
								order_schema.get('order').update({'invoice_date': invoice.date_invoice and str(invoice.date_invoice)})
								order_schema.get('order').update({'total_paid_real': order.amount_total and str(order.amount_total)})
								# order.get('order').update({'current_state': str(status_ids[0].presta_id)})
							else:
								invoice_not_done = True
						if invoice_not_done == False:
							status_ids = status_obj.search([('name', '=', 'Payment accepted')])
							order_schema.get('order').update({'current_state': status_ids[0].presta_id and str(status_ids[0].presta_id)})
							order.order_status = status_ids[0].id

						picking_not_done = False
						for picking in order.picking_ids:
							if picking.state == 'done':
								order_schema.get('order').update({'delivery_number': picking.name and str(picking.name)})
								order_schema.get('order').update({'delivery_date': picking.scheduled_date and str(picking.scheduled_date)})
								# order_schema.get('order').update({'current_state': status_ids[0].presta_id and str(status_ids[0].presta_id)})
							else:
								picking_not_done = True
						if picking_not_done == False:
							status_ids = status_obj.search([('name', '=', 'Shipped')])
							print('----------status_ids----',status_ids)
							if status_ids:
								order_schema.get('order').update({'current_state': status_ids[0].presta_id and str(status_ids[0].presta_id)})
								order.order_status = status_ids[0].id
					lines = []
					cart_line_list = []
					if len(order.order_line)>1:
						for line in order.order_line:
							lines.append({
								 'product_attribute_id': line.product_id.combination_id and str(line.product_id.combination_id) or '0',
								 'product_id': line.product_id.product_tmpl_id and line.product_id.product_tmpl_id.presta_id and str(line.product_id.product_tmpl_id.presta_id),
								 'product_name': line.name and str(line.name),
								 'product_price': str(int(line.price_unit)),
								 'product_quantity': str(int(line.product_uom_qty)),
								 'product_reference': line.product_id.default_code and str(line.product_id.default_code),
							})
							cart_line_list.append({'id_address_delivery': order.partner_id.address_id and str(order.partner_id.address_id),
												   'id_product_attribute': line.product_id.combination_id and str(line.product_id.combination_id) or '0',
												   'id_product': line.product_id.product_tmpl_id and line.product_id.product_tmpl_id.presta_id and str(line.product_id.product_tmpl_id.presta_id),
												   'quantity': line.product_uom_qty and str(line.product_uom_qty),
							})
					else:
						line = order.order_line[0]
						lines = {
							'product_attribute_id': line.product_id.combination_id and str(line.product_id.combination_id) or '0',
							'product_id': line.product_id.product_tmpl_id and line.product_id.product_tmpl_id.presta_id and str(line.product_id.product_tmpl_id.presta_id),
							'product_name': line.name and str(line.name),
							'product_price': str(int(line.price_unit)),
							'product_quantity': str(int(line.product_uom_qty)),
							'product_reference': line.product_id.default_code and str(line.product_id.default_code),
						}
						cart_line_list = {
									'id_address_delivery': order.partner_id.address_id and str(order.partner_id.address_id),
									'id_product_attribute': line.product_id.combination_id and str(line.product_id.combination_id) or '0',
									'id_product': line.product_id.product_tmpl_id and line.product_id.product_tmpl_id.presta_id and str(line.product_id.product_tmpl_id.presta_id),
									'quantity': line.product_uom_qty and str(line.product_uom_qty),
						}
					order_schema.get('order').get('associations').get('order_rows').update({
						# 'attrs': {'nodeType': 'order_row',
						#           'virtualEntity': 'true'},
						'order_row': lines,
					})
					carts_schema.get('cart').update({
						'id_carrier': order.carrier_prestashop and order.carrier_prestashop.presta_id and str(order.carrier_prestashop.presta_id),
						'id_address_delivery': order.partner_id.address_id and str(order.partner_id.address_id),
						'id_shop': shop.presta_id and str(shop.presta_id),
						'id_customer': order.partner_id and order.partner_id.presta_id and str(order.partner_id.presta_id),
						'id_lang': shop.get_languange(prestashop, order.partner_id.lang),
						'id_address_invoice' : order.partner_id.address_id and str(order.partner_id.address_id),
						'id_currency': shop.get_currency(prestashop, shop.pricelist_id.currency_id),
						# 'id_shop_group' : '1',
						'mobile_theme': '0',
						'id_shop': shop.presta_id and str(shop.presta_id),
						# 'gift': '0',
						# 'gift_message': '',
						# 'id_guest': '1',
					})
					carts_schema.get('cart').get('associations').get('cart_rows').update({
						# 'attrs': {'node_type': 'cart_row',
						#           'virtual_entity': 'true'},
						# 'delivery_option': 'a:1:{i:3;s:2:"2,";}',
						'cart_row': cart_line_list,
						})
					sale_gift_ids = sale_order_line_obj.search([('order_id', '=', order.id), ('gift', '=', True)])
					if sale_gift_ids:
						for gift_id in sale_gift_ids:
							gift_msg = gift_id.gift_message
							wrapping_cost = gift_id.wrapping_cost or '0.000'
							carts_schema.get('cart').update({
								'gift': '1',
								'gift_message': gift_msg and str(gift_msg),
							})
							order_schema.get('order').update(
								{'gift': '1',
								 'gift_message': gift_msg and str(gift_msg),
								 'total_wrapping': wrapping_cost and str(wrapping_cost),
								 'total_wrapping_tax_excl': wrapping_cost and str(wrapping_cost),
								 })
					presta_cart = prestashop.add('carts', carts_schema)
					cart_presta_id = self.get_value_data(presta_cart.get('prestashop').get('cart').get('id'))[0]
					order.write({
						'to_be_exported':False
						})
					if cart_presta_id:
						order_schema.get('order').update({
							'id_cart' : cart_presta_id and str(cart_presta_id),
						})
					presta_orders = prestashop.add('orders', order_schema)
			except Exception as e:
				if self.env.context.get('log_id'):
					log_id = self.env.context.get('log_id')
					self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
				else:
					log_id_obj = self.env['prestashop.log'].create(
						{'all_operations': 'export_order_status', 'error_lines': [(0, 0, {'log_description': str(e), })]})
					log_id = log_id_obj.id
				new_context = dict(self.env.context)
				new_context.update({'log_id': log_id})
				self.env.context = new_context