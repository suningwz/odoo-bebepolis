# -*- coding: UTF-8 -*-

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    coupon_pos_ids = fields.One2many(
        'pos.coupon', 'partner_id', string="Coupons Applied From POS")
