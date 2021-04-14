# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_session_id = fields.Many2one('pos.session', string="POS session", ondelete='cascade')
