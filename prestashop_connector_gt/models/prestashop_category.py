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


import logging
import pytz
from datetime import datetime
from odoo import api, fields, models, _
from xml.dom.minidom import parse, parseString
import xml.etree.ElementTree as ET
# from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from odoo.addons.prestashop_connector_gt.prestapyt import PrestaShopWebServiceError, PrestaShopWebService, PrestaShopWebServiceDict


    
class prestashop_category(models.Model):
    _name='prestashop.category'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    # is_root = fields.Boolean('Is Root Category?' )
    # presta_active = fields.Boolean(string='Active')
    # code = fields.Char(string='Code', required=True)
    # description = fields.Text(string='Description')
    # parent_id = fields.Char(string='ID Parent')
    # visibe = fields.Boolean(string='Visible')
    # shop_id = fields.Many2one('sale.shop', string='Shop ID')
    # presta_shop_id = fields.Char(string='Presta Shop ID')
    # shop_ids = fields.Many2many('sale.shop', 'category_shop_rel', 'categ_id', 'shop_id', string="Shop")


    # from product_category
    presta_id = fields.Char("Presta ID")
    # write_date = fields.Datetime(string="Write Date")
    # shop_id = fields.Many2one('sale.shop', 'Shop ID')
    shop_ids = fields.Many2many('sale.shop', 'presta_categ_shop_rel', 'categ_id', 'shop_id', string="Shop")
    to_be_exported = fields.Boolean(string="To be exported?")
    parent_path = fields.Char(index=True)

    #from addons product
    name = fields.Char('Name', index=True, required=True, translate=True)
    parent_id = fields.Many2one('prestashop.category', 'Parent Category', ondelete='cascade')
    # child_id = fields.One2many('prestashop.category', 'parent_id', 'Child Categories')
    # type = fields.Selection([
    #     ('view', 'View'),
    #     ('normal', 'Normal')], 'Category Type', default='normal',
    #     help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure.")
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products under this category (Does not consider the children categories)")


    def _compute_product_count(self):
        for rec in self:
            product_ids = self.env['product.template'].search([('presta_categ_id','=',rec.id)])
            rec.product_count = len(product_ids)

    # @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):

    #     # if not args:
    #     #     args = []       
    #     if name:
    #         # Be sure name_search is symetric to name_get
    #         category_names = name.split(' / ')
    #         print ("category_names--->",category_names)
    #         # parents = list(category_names)
    #         # print ("parents---->",parents)
    #         # child = parents.pop()
    #         # domain = [('name', operator, child)]
    #         # if parents:
    #         #     names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
    #         #     category_ids = [name_id[0] for name_id in names_ids]
    #         #     if operator in expression.NEGATIVE_TERM_OPERATORS:
    #         #         categories = self.search([('id', 'not in', category_ids)])
    #         #         domain = expression.OR([[('parent_id', 'in', categories.ids)], domain])
    #         #     else:
    #         #         domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
    #         #     for i in range(1, len(category_names)):
    #         #         domain = [[('name', operator, ' / '.join(category_names[-1 - i:]))], domain]
    #         #         if operator in expression.NEGATIVE_TERM_OPERATORS:
    #         #             domain = expression.AND(domain)
    #         #         else:
    #         #             domain = expression.OR(domain)
    #         # categories = self.search(expression.AND([domain, args]), limit=limit)
    #     else:
    #         categories = self.search(args, limit=limit)
    #     return categories.name_get()

