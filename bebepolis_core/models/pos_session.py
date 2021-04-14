# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    bank_statement_line_ids = fields.One2many('account.bank.statement.line', 'pos_session_id', string='Bank statement')
    amount_taken_from_cash_box = fields.Float(compute='_compute_amount_taken_from_cash_box', string='Taken form cashbox', default=0.0, store=True)
    amount_added_to_cash_box = fields.Float(compute='_compute_amount_taken_from_cash_box', string='Add to cashbox', default=0.0, store=True)
    
    @api.depends('bank_statement_line_ids')
    def _compute_amount_taken_from_cash_box(self):
        for session in self:
            session.amount_taken_from_cash_box = sum([bnk_st_line.amount for bnk_st_line in session.bank_statement_line_ids if bnk_st_line.amount < 0.0])
            session.amount_added_to_cash_box = sum([bnk_st_line.amount for bnk_st_line in session.bank_statement_line_ids if bnk_st_line.amount > 0.0])

    @api.model
    def get_payment_method_amount(self):
        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', self.order_ids.ids)]).ids
        payments = []
        if payment_ids:
            self.env.cr.execute("""
                SELECT method.name, sum(amount) total
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %s
                GROUP BY method.name
            """, (tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()
        return payments
