# -*- coding: utf-8 -*-

from odoo.addons.point_of_sale.wizard.pos_box import PosBoxOut


class PosBoxOut(PosBoxOut):
    _inherit = 'cash.box.out'

    def _calculate_values_for_statement_line(self, record):
        values = super(PosBoxOut, self)._calculate_values_for_statement_line(record)
        active_model = self.env.context.get('active_model', False)
        active_ids = self.env.context.get('active_ids', [])
        if active_model == 'pos.session' and active_ids:
            values['pos_session_id'] = self.env[active_model].browse(active_ids)[0].id
        return values
