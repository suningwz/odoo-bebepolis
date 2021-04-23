# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    def get_pos_order_fields(self):
        res = super(PosOrder, self).get_pos_order_fields()
        res.append('note')
        return res

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder, self)._process_order(order, draft, existing_order)
        order_id = self.env['pos.order'].browse(res)
        if order['data']['note']:
            order_id.write({'note': order['data']['note']})
        return res

