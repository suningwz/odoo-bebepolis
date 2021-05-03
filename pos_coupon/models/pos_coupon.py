# -*- coding: UTF-8 -*-

import random
import string
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosCoupon(models.Model):
    _name = 'pos.coupon'
    _rec_name = 'coupon_code'
    _description = 'Coupon code '

    _sql_constraints = [
        ('pos_coupon_code_uniq', 'unique (coupon_code)', "Cupon code exists!"),
    ]

    coupon_code = fields.Char(string="Code", default=lambda self: self.env['ir.sequence'].next_by_code('bb.polis.coupon.sequence'), required=True)
    short_description = fields.Char(string="Description")
    partner_id = fields.Many2one('res.partner', string="Customer")
    coupon_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
    ], default='fixed')
    amount = fields.Float(string='Amount', digits=(6, 4))
    available_amount = fields.Float(string='Available amount', digits=(6, 4), store=True, compute='compute_remaining_amount')
    coupon_history_ids = fields.One2many('pos.coupon.uses.history', 'coupon_id', string='Use\'s logs')
    active = fields.Boolean(string='Active')
    valid_date = fields.Date(string='It\'s valid until')

    @api.depends('coupon_history_ids')
    def compute_remaining_amount(self):
        log_cls = self.env['pos.coupon.uses.history']
        for c in self:
            log_obj = log_cls.search(
                [('coupon_id', '=', c.id)], order="id DESC", limit=1)
            if log_obj:
                c.available_amount = log_obj.credit
            else: c.available_amount = self.amount

    def _create_log(self):
        log_id = self.sudo().env['pos.coupon.uses.history'].create({
            'partner_id': self.partner_id.id,
            'name': _('Coupon used for %s') % self.debit,
            'debit': self.debit if self.debit < 0 else -1 * self.debit,
            'coupon_id': self.self.id,
        })
        return log_id


class PosCouponHistory(models.Model):
    _name = 'pos.coupon.uses.history'
    _description = 'Coupon history'

    coupon_id = fields.Many2one('pos.coupon', string='Coupon', required=True)
    debit = fields.Float(string='Last Amount', digits=(6, 4), required=True)
    credit = fields.Float(string='Amount Available', digits=(6, 4), required=True)
    name = fields.Char(string='Short description')

    @api.model
    def create(self, vals):
        last_op = self.search([('coupon_id', '=', vals['coupon_id'])], order="id DESC", limit=1)
        if last_op:
            last_cr = last_op.credit
        else:
            last_cr = self.env['pos.coupon'].search(
                [('id', '=', vals['coupon_id'])], limit=1).amount
        
        vals['credit'] = last_cr + vals['debit']
        
        if vals['credit'] < 0:
            raise ValidationError(_("Insufficient credit."))
        
        return super(PosCouponHistory, self).create(vals)

    @api.constrains('debit', 'credit')
    def _constrains_debit_credit(self):
        if self.credit < 0:
            raise ValidationError(_("Insufficient credit."))
        if self.debit >= 0:
            raise ValidationError(_("Discounted value must be a negative number."))
