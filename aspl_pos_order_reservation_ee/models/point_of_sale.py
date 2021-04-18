# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

import logging
from collections import defaultdict
from odoo import tools, models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import Warning, UserError
import time
from pytz import timezone
from odoo.tools import float_is_zero
import psycopg2

_logger = logging.getLogger(__name__)


class pos_order(models.Model):
    _inherit = "pos.order"

    def update_delivery_date(self, delivery_date):
        res = self.write({'delivery_date': datetime.strptime(delivery_date, '%Y-%m-%d')})
        if res:
            return self.read()[0]
        return False

    def test_paid(self):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self:
            if order.amount_due == 0.00:
                return True

            if order.lines and not order.amount_total:
                continue
            if (not order.lines) or (abs(order.amount_total - order.amount_paid) > 0.00001):
                return False
        return True

    def _order_fields(self, ui_order):
        res = super(pos_order, self)._order_fields(ui_order)
        res.update({
            'order_booked': ui_order.get('reserved', False),
            'reserved': ui_order.get('reserved', False),
            'delivery_date': ui_order.get('delivery_date', False),
            'cancel_order': ui_order.get('cancel_order_ref', False),
            'is_cancel_order': ui_order.get('cancel_order', False),
            'customer_email': ui_order.get('customer_email', False),
            'fresh_order': ui_order.get('fresh_order', False),
            'partial_pay': ui_order.get('partial_pay', False),
            'picking_id': ui_order.get('picking_id', False),
            'amount_paid':ui_order.get('amount_paid', False),
        })
        return res

    def write(self, vals):
        for order in self:
            if order.name == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('aspl.pos.order')
        return super(pos_order, self).write(vals)

    def action_pos_order_paid(self):
        if not self._is_pos_order_paid():
            if self.reserved:
                return self.do_internal_transfer()
            elif self.order_status == 'partial' and self.is_cancel_order:
                return self.do_internal_transfer()
            else:
                raise UserError(_("Order %s is not fully paid.") % self.name)
        else:
            if self.order_status == "full":
                self.write({'state': 'cancel'})
                return self.do_internal_transfer()
            elif self.order_status == "partial":
                if self.do_internal_transfer():
                    self.write({'state': 'paid'})
                    return self.do_customer_picking()
            elif self.order_status == "not_applied":
                self.write({'state': 'paid'})
                return self.do_customer_picking()
            else:
                self.write({'state': 'paid'})
                return self.create_picking()

    @api.model
    def _process_order(self, order, draft, existing_order):
        if order.get('data').get('old_order_id'):
            pos_line_obj = self.env['pos.order.line']
            order = order['data']
            pos_order = self.browse([order.get('old_order_id')])
            prec_acc = pos_order.pricelist_id.currency_id.decimal_places
            old_order = self.search_read([('id', '=', pos_order.id)])
            old_session_id = old_order[0].get('session_id')[0]
            pos_line_ids = pos_line_obj.search([('order_id', '=', pos_order.id)])
            temp = order.copy()
            if pos_line_ids:
                if not order.get('cancel_order'):
                    for line_id in pos_line_ids:
                        line_id.unlink()
                # cancel_line_ids = self.env['pos.order.line'].create(temp['lines'])
                # temp = order.copy()
                temp['name'] = old_order[0]['pos_reference']
                temp['pos_reference'] = old_order[0]['pos_reference']
                old_order[0]['pos_session_id'] = temp['pos_session_id'];
                old_order[0]['lines'] = temp['lines'];
                total_price = 0.00
                for line in temp.get('lines'):
                    linedict = line[2]
                    if pos_order.session_id.config_id.prod_for_payment.id == linedict.get('product_id'):
                        temp.get('lines').remove(line)
                    if pos_order.session_id.config_id.refund_amount_product_id.id == linedict.get('product_id'):
                        temp.get('lines').remove(line)
                total_price = old_order[0].get('amount_total')

                for line in temp.get('lines'):
                    total_price += sum([line[2].get('price_subtotal_incl')])
                if (total_price > old_order[0].get('amount_total')):
                    total_price = old_order[0].get('amount_total')
                temp['amount_total'] = total_price
                pos_order.write(self._order_fields(temp))
            account_payment = self.env['account.payment']
            for payments in order['statement_ids']:
                if old_session_id == pos_order.session_id.id:
                    pos_order.with_context({'from_pos': True}).add_payment(self._payment_fields(pos_order, payments[2]))
                else:
                    pos_payment_method = self.env['pos.payment.method'].browse(payments[2].get('payment_method_id'))
                    if pos_payment_method.is_cash_count:
                        account_journal_obj = pos_payment_method.cash_journal_id
                    else:
                        account_journal_obj = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
                    if account_journal_obj.type == 'cash' and order.get('amount_return'):
                        amount_paid = payments[2].get("amount") - order.get('amount_return')
                    else:
                        amount_paid = payments[2].get("amount")

                    if amount_paid < 0:
                        payment_type = 'outbound'
                        amount = -1 * amount_paid
                    else:
                        payment_type = 'inbound'
                        amount = amount_paid

                    payment_obj = account_payment.create({
                        'payment_type': payment_type,
                        'partner_id': pos_order.partner_id.id,
                        'partner_type': 'customer',
                        'payment_method_id': account_journal_obj.inbound_payment_method_ids.id,
                        "amount": amount,
                        "journal_id": account_journal_obj.id,
                        'currency_id': self.env.user.company_id.currency_id.id,
                    })
                    payment_obj.post()
                    pos_order.with_context({'from_pos': True}).add_payment(self._payment_fields(pos_order, payments[2]))
            if pos_order._is_pos_order_paid():
                pos_order.write({'state': 'done'})

            # for amount return cash
            if not draft and not float_is_zero(order['amount_return'],
                                               prec_acc):
                pos_session = self.env['pos.session'].browse(order['pos_session_id'])
                cash_payment_method = pos_session.payment_method_ids.filtered(
                    'is_cash_count')[:1]
                if not cash_payment_method:
                    raise UserError(_(
                        "No cash statement found for this session. Unable "
                        "to record returned cash."))
                return_payment_vals = {
                    'name': _('return'),
                    'pos_order_id': pos_order.id,
                    'amount': -order['amount_return'],
                    'payment_date': fields.Date.context_today(self),
                    'payment_method_id': cash_payment_method.id,
                }
                pos_order.add_payment(return_payment_vals)
            if not draft:
                try:
                    pos_order.action_pos_order_paid()
                except psycopg2.DatabaseError:
                    # do not hide transactional errors, the order(s) won't be saved!
                    raise
                except Exception as e:
                    _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
            return pos_order.id
        else:
            to_invoice = order['to_invoice'] if not draft else False
            order = order['data']
            pos_session = self.env['pos.session'].browse(order['pos_session_id'])
            if pos_session.state == 'closing_control' or pos_session.state == 'closed':
                order['pos_session_id'] = self._get_valid_session(order).id

            pos_order = False
            if not existing_order:
                pos_order = self.create(self._order_fields(order))
            else:
                pos_order = existing_order
                pos_order.lines.unlink()
                order['user_id'] = pos_order.user_id.id
                pos_order.write(self._order_fields(order))
            self._process_payment_lines(order, pos_order, pos_session, draft)
            if not draft:
                try:
                    pos_order.action_pos_order_paid()
                except psycopg2.DatabaseError:
                    # do not hide transactional errors, the order(s) won't be saved!
                    raise
                except Exception as e:
                    _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            if to_invoice and not order.get('set_as_draft') and not order.get('reserved') and \
                    not order.get('partial_pay'):
                pos_order.action_pos_order_invoice()
                pos_order.account_move.sudo().with_context(force_company=self.env.user.company_id.id).post()

            self._process_payment_lines(order, pos_order, pos_session, draft)
            return pos_order.id

    def do_customer_picking(self):
        move_lines = []
        for order in self:
            Move = self.env['stock.move']
            moves = Move
            if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                continue
            picking_type = order.picking_type_id
            StockWarehouse = self.env['stock.warehouse']
            location_id = order.config_id.reserve_stock_location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            else:
                if (not picking_type) or (not picking_type.default_location_dest_id):
                    customerloc, supplierloc = StockWarehouse._get_partner_locations()
                    destination_id = customerloc.id
                else:
                    destination_id = picking_type.default_location_dest_id.id
            if picking_type:
                picking_vals = {
                    'picking_type_id': picking_type.id,
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                    'state': 'draft',
                    'origin': order.name
                }
                picking_obj = self.env['stock.picking'].create(picking_vals)

            if location_id:
                temp_move_lines = []
                product_dict = {}
                lot_quantity_dict = {}
                for line in order.lines:
                    if line.product_id.type != "service":
                        if line.product_id.default_code:
                            name = [line.product_id.default_code]
                        else:
                            name = line.product_id.name
                        for lot in line.pack_lot_ids:
                            if lot.lot_name not in lot_quantity_dict:
                                lot_quantity_dict[lot.lot_name] = line.qty/len(line.pack_lot_ids.ids)
                            else:
                                lot_quantity_dict[lot.lot_name] += (line.qty/len(line.pack_lot_ids.ids))
                        if str(line.product_id.id) not in product_dict:
                            product_dict[str(line.product_id.id)] = line.qty
                        else:
                            product_dict[str(line.product_id.id)] += line.qty
                for product, qty in product_dict.items():
                    move_vals = {
                        'name': name,
                        'product_uom': line.product_id.uom_id.id,
                        'picking_id': picking_obj.id,
                        'picking_type_id': picking_type.id,
                        'product_id': int(product),
                        'product_uom_qty': abs(qty),
                        'state': 'draft',
                        'location_id': location_id,
                        'location_dest_id': destination_id,
                    }
                    moves_id = Move.create(move_vals)
                    line.write({'picking_id': picking_obj.id})
                    if moves_id and not picking_obj:
                        moves._action_assign()
                        moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()
                    if picking_obj:
                        picking_obj.action_confirm()
                        qty_done = 0
                        if lot_quantity_dict:
                            pack_lots = []
                            StockProductionLot = self.env['stock.production.lot']
                            for lot_name, lot_qty in lot_quantity_dict.items():
                                if lot_qty > 0:
                                    stock_production_lot = StockProductionLot.search(
                                        [('name', 'ilike', lot_name)])
                                    if stock_production_lot:
                                        qty = 1.0
                                        if stock_production_lot.product_id.tracking == 'lot':
                                            qty = abs(lot_qty)
                                        qty_done += qty
                                        pack_lots.append({'lot_id': stock_production_lot.id, 'qty': qty,
                                                          'product_id': stock_production_lot.product_id.id})
                            for move in picking_obj.move_lines:
                                if move.product_id.tracking == 'lot' or move.product_id.tracking == 'serial':
                                    for pack_lot in pack_lots:
                                        lot_id, qty, product_id = pack_lot['lot_id'], pack_lot['qty'], pack_lot[
                                            'product_id']
                                        vals = {
                                            'picking_id': move.picking_id.id,
                                            'move_id': move.id,
                                            'product_id': product_id,
                                            'product_uom_id': move.product_uom.id,
                                            'qty_done': qty,
                                            'location_id': move.location_id.id,
                                            'location_dest_id': move.location_dest_id.id,
                                            'lot_id': lot_id,
                                        }
                                        self.env['stock.move.line'].create(vals)
                                    if not pack_lots and not float_is_zero(qty_done,
                                                                           precision_rounding=move.product_uom.rounding):
                                        if len(move._get_move_lines()) < 2:
                                            move.quantity_done = qty_done
                                        else:
                                            move._set_quantity_done(qty_done)
                        if product_dict:
                            for move in picking_obj.move_lines:
                                if move.product_id.tracking == 'none':
                                    move._set_quantity_done(product_dict.get(str(move.product_id.id)))
                        picking_obj.action_assign()
                        picking_obj.button_validate()
                        stock_transfer_id = self.env['stock.immediate.transfer'].search(
                            [('pick_ids', '=', picking_obj.id)], limit=1)
                        if stock_transfer_id:
                            stock_transfer_id.process()
                        order.write({'picking_id': picking_obj.id})

                query = ''' UPDATE pos_order SET unreserved=True,
                                               picking_id='%s'
                                               WHERE id=%s''' % (picking_obj.id, order.id)
                self._cr.execute(query)
        return True

    def do_internal_transfer(self):
        for order in self:
            if order.config_id.reserve_stock_location_id:
                is_cancel = False
                Move = self.env['stock.move']
                moves = Move
                warehouse_obj = self.env['stock.warehouse'].search([
                    ('lot_stock_id', '=', order.config_id.picking_type_id.default_location_src_id.id)], limit=1)
                if warehouse_obj:
                    picking_type_obj = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', warehouse_obj.id), ('code', '=', 'internal')])
                for line in order.lines:
                    if not line.picking_id and line.product_id.type != "service":
                        temp_move_lines = []
                        if picking_type_obj:
                            picking_vals = {
                                'picking_type_id': picking_type_obj.id,
                                'location_id': order.config_id.picking_type_id.default_location_src_id.id,
                                'location_dest_id': order.config_id.reserve_stock_location_id.id,
                                'state': 'draft',
                                'origin': order.name
                            }
                            if is_cancel:
                                picking_vals.update({
                                    'location_dest_id': order.config_id.picking_type_id.default_location_src_id.id,
                                    'location_id': order.config_id.reserve_stock_location_id.id,
                                })
                            picking_obj = self.env['stock.picking'].create(picking_vals)
                            if line.product_id.default_code:
                                name = [line.product_id.default_code]
                            else:
                                name = line.product_id.name
                            if not line.picking_id and line.product_id.type != "service":
                                move_vals = {
                                    'name': name,
                                    'product_uom': line.product_id.uom_id.id,
                                    'picking_id': picking_obj.id,
                                    'picking_type_id': picking_type_obj.id,
                                    'product_id': line.product_id.id,
                                    'product_uom_qty': abs(line.qty),
                                    'state': 'draft',
                                    'location_id': order.config_id.picking_type_id.default_location_src_id.id if line.qty >= 0 else order.config_id.reserve_stock_location_id.id,
                                    'location_dest_id': order.config_id.reserve_stock_location_id.id if line.qty > 0 else order.config_id.picking_type_id.default_location_src_id.id,
                                }
                                moves_id = Move.create(move_vals)
                                # line.write({'picking_id': picking_obj.id})
                                if moves_id and not picking_obj:
                                    moves._action_assign()
                                    moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()
                                if picking_obj:
                                    picking_obj.action_confirm()
                                    if not self.check_lot_products(picking_obj, line.order_id, line.id):
                                        picking_obj.action_assign()
                                        picking_obj.button_validate()
                                        stock_transfer_id = self.env['stock.immediate.transfer'].search(
                                            [('pick_ids', '=', picking_obj.id)], limit=1)
                                        if stock_transfer_id:
                                            stock_transfer_id.process()
                                        line.picking_id = picking_obj.id
        return True

    def check_lot_products(self, picking, order, line_id):
        StockProductionLot = self.env['stock.production.lot']
        PosPackOperationLot = self.env['pos.pack.operation.lot']
        has_wrong_lots = False
        for move in picking.move_lines:
            picking_type = picking.picking_type_id
            lots_necessary = True
            if picking_type:
                lots_necessary = picking_type and picking_type.use_existing_lots
                qty_done = 0
                pack_lots = []
                if line_id:
                    pos_pack_lots = PosPackOperationLot.search(
                        [('pos_order_line_id', '=', line_id), ('product_id', '=', move.product_id.id)])
                else:
                    pos_pack_lots = PosPackOperationLot.search(
                        [('order_id', '=', order.id), ('product_id', '=', move.product_id.id)])
                if pos_pack_lots and lots_necessary:
                    for pos_pack_lot in pos_pack_lots:
                        stock_production_lot = StockProductionLot.search([('name', '=', pos_pack_lot.lot_name), ('product_id', '=', move.product_id.id)])
                        if stock_production_lot:
                            # a serialnumber always has a quantity of 1 product, a lot number takes the full quantity of the order line
                            qty = 1.0
                            if stock_production_lot.product_id.tracking == 'lot':
                                qty = abs(pos_pack_lot.pos_order_line_id.qty)
                            qty_done += qty
                            pack_lots.append({'lot_id': stock_production_lot.id, 'qty': qty})
                        else:
                            has_wrong_lots = True
                elif move.product_id.tracking == 'none' or not lots_necessary:
                    qty_done = move.product_uom_qty
                else:
                    has_wrong_lots = True
                for pack_lot in pack_lots:
                    lot_id, qty = pack_lot['lot_id'], pack_lot['qty']
                    self.env['stock.move.line'].create({
                        'picking_id': move.picking_id.id,
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': lot_id,
                    })
                if not pack_lots and not float_is_zero(qty_done, precision_rounding=move.product_uom.rounding):
                    if len(move._get_move_lines()) < 2:
                        move.quantity_done = qty_done
                    else:
                        move._set_quantity_done(qty_done)
            return has_wrong_lots

    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_due(self):
        for each in self:
            each.amount_due = each.amount_total - each.amount_paid

    @api.depends('lines')
    def _find_order_status(self):
        for order in self:
            product_ids = list(order.lines.mapped('product_id'))
            item_count = sum(order.lines.filtered(lambda line : line.product_id.type !='service').mapped('qty'))
            if item_count == 0:
                order.order_status = "full"
            else:
                if order.is_cancel_order:
                    order.order_status = "partial"
                else:
                    order.order_status = "not_applied"

    order_status = fields.Selection([('full', 'Fully Cancelled'), ('partial', 'Partially Cancelled'), ('not_applied', 'Not-Applicable')],
                                    'Order Status', store=True, compute="_find_order_status")
    reserved = fields.Boolean("Reserved", readonly=True)
    partial_pay = fields.Boolean("Partial Pay", readonly=True)
    old_session_ids = fields.Many2many('pos.session', string="Old sessions")
    order_booked = fields.Boolean("Booked", readonly=True)
    unreserved = fields.Boolean("Unreserved")
    amount_due = fields.Float(string='Amount Due', compute='_compute_amount_due')
    delivery_date = fields.Date(string="Delivery Date")
    cancel_order = fields.Char('Cancel Order')
    is_cancel_order = fields.Boolean("Is Cancel Order")
    customer_email = fields.Char('Customer Email')
    fresh_order = fields.Boolean("Fresh Order")

    @api.model
    def add_payment(self, data):
        """Create a new payment for the order"""
        if data['amount'] == 0.0:
            return
        return super(pos_order, self).add_payment(data)

    def send_reserve_mail(self):
        if self and self.customer_email and self.reserved and self.fresh_order:
            try:
                template_id = self.env['ir.model.data'].get_object_reference('aspl_pos_order_reservation_ee',
                                                                             'email_template_pos_ereceipt')
                template_obj = self.env['mail.template'].browse(template_id[1])
                template_obj.send_mail(self.id, force_send=True, raise_exception=True)
            except Exception as e:
                _logger.error('Unable to send email for order %s', e)

    @api.model
    def ac_pos_search_read(self, domain):
        get_domain = domain.get('domain')
        search_vals = self.search_read(get_domain,
                                       ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved',
                                        'write_date', 'id', 'partner_id', 'lines', 'delivery_date', 'amount_total',
                                        'amount_due'])

        user_id = self.env['res.users'].browse(self._uid)
        tz = False
        if self._context and self._context.get('tz'):
            tz = timezone(self._context.get('tz'))
        elif user_id and user_id.tz:
            tz = timezone(user_id.tz)
        if tz:
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            result = []

            for val in search_vals:
                # temp = self.search_read([('id', '=', val.id)])
                if sign == '-':
                    val.update({
                        'date_order': val.get('date_order') - timedelta(hours=hour_tz, minutes=min_tz)
                    })
                elif sign == '+':
                    val.update({
                        'date_order': val.get('date_order') + timedelta(hours=hour_tz, minutes=min_tz)
                    })
                result.append(val)
        else:
            result = search_vals
        for res in result:
            line_dict = self.env['pos.order.line'].browse(res.get('lines'))
            if line_dict:
                res['lines'] = line_dict.read()
        return result

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = []
        for order in orders:
            existing_order = False
            if 'server_id' in order['data']:
                existing_order = self.env['pos.order'].search(
                    ['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])],
                    limit=1)
            if (existing_order and existing_order.state == 'draft') or not existing_order:
                pos_order = self._process_order(order, draft, existing_order)
                if pos_order:
                    to_be_cancelled_items = {}
                    order = order['data']
                    for line in order.get('lines'):
                        if line[2].get('cancel_process'):
                            if line[2].get('product_id') in to_be_cancelled_items:
                                to_be_cancelled_items[line[2].get('product_id')] = to_be_cancelled_items[
                                                                                       line[2].get('product_id')] + line[2].get('qty')
                            else:
                                to_be_cancelled_items.update({line[2].get('product_id'): line[2].get('qty')})
                    for line in order.get('lines'):
                        for item_id in to_be_cancelled_items:
                            cancel_lines = []
                            if line[2].get('cancel_process'):
                                cancel_lines = self.browse([line[2].get('cancel_process')[0]]).lines
                            for origin_line in cancel_lines:
                                if to_be_cancelled_items[item_id] == 0:
                                    continue
                                if origin_line.qty > 0 and item_id == origin_line.product_id.id:
                                    if (to_be_cancelled_items[item_id] * -1) >= origin_line.qty:
                                        ret_from_line_qty = 0
                                        to_be_cancelled_items[item_id] = to_be_cancelled_items[
                                                                             item_id] + origin_line.qty
                order_ids.append(pos_order)

        return self.env['pos.order'].search_read(domain=[('id', 'in', order_ids)], fields=['id', 'pos_reference'])


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_location(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)],
                                                  limit=1).lot_stock_id

    enable_order_reservation = fields.Boolean('Enable Order Reservation')
    reserve_stock_location_id = fields.Many2one('stock.location', 'Reserve Stock Location')
    cancellation_charges_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')],
                                                 'Cancellation Charges Type')
    cancellation_charges = fields.Float('Cancellation Charges')
    cancellation_charges_product_id = fields.Many2one('product.product', 'Cancellation Charges Product')
    last_days = fields.Char("Last Days")
    record_per_page = fields.Integer("Record Per Page")
    prod_for_payment = fields.Many2one('product.product', string='Paid Amount Product',
                                       help="This is a dummy product used when a customer pays partially. This is a workaround to the fact that Odoo needs to have at least one product on the order to validate the transaction.")
    refund_amount_product_id = fields.Many2one('product.product', 'Refund Amount Product')
    enable_pos_welcome_mail = fields.Boolean("Send Welcome Mail")
    allow_reservation_with_no_amount = fields.Boolean("Allow Reservation With 0 Amount")
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)


class pos_order_line(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def create(self, values):
        res = super(pos_order_line, self).create(values)
        if values.get('cancel_item_id'):
            line_id = self.browse(values.get('cancel_item_id'))
            if values.get('new_line_status'):
                line_id.write({'line_status': values.get('new_line_status')})
        return res

    cancel_item = fields.Boolean("Cancel Item")
    line_status = fields.Selection(
        [('nothing', 'Nothing'), ('full', 'Fully Cancelled'), ('partial', 'Partially Cancelled')],
        'Order Status', default="nothing")
    picking_id = fields.Many2one('stock.picking', string = "Picking Id")

    @api.model
    def get_order_line_data(self, fields, order_lines):
        lines = []
        lot_by_line = {}
        line_by_id = {}
        product_by_lot = {}
        product_by_quantity = {}
        order_lines_data = self.search([('id', 'in', order_lines), ('product_id.type', '!=', 'service')])
        for each in order_lines_data:
            for lot in each.pack_lot_ids:
                if lot.lot_name not in product_by_lot:
                    product_by_lot[lot.lot_name] = (each.qty/len(each.pack_lot_ids.ids))
                else:
                    product_by_lot[lot.lot_name] += (each.qty/len(each.pack_lot_ids.ids))
            if each.product_id.id not in product_by_quantity:
                product_by_quantity[each.product_id.id] = each.qty
            else:
                product_by_quantity[each.product_id.id] += each.qty
        for line in self.search_read([('id', 'in', order_lines), ('product_id.type', '!=', 'service'), ('qty', '>', 0)]):
            line_by_id[line.get('id')] = line
            lines.append(line)
        pack_lot_data = self.env['pos.pack.operation.lot'].search_read([('pos_order_line_id', 'in', order_lines)])
        for lot in pack_lot_data:
            if not lot.get('pos_order_line_id')[0] in lot_by_line:
                lot_by_line[lot.get('pos_order_line_id')[0]] = [lot]
            else:
                lot_by_line[lot.get('pos_order_line_id')[0]].append(lot)
        data = {
            'lines': lines,
            'line': line_by_id,
            'pack_lots_by_line': lot_by_line,
            'pack_lots': pack_lot_data,
            'quantity_dict': product_by_lot,
            'product_by_quantity': product_by_quantity,
            'line_search_read': self.search_read([('id', 'in', order_lines)])
        }
        return [data]

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start', 'cash_register_id')
    def _compute_cash_balance(self):
        if not self.config_id.enable_order_reservation:
            super(PosSession, self)._compute_cash_balance()
        else:
            for session in self:
                cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
                if cash_payment_method:
                    total_cash_payment = sum(session.order_ids.mapped('payment_ids').filtered(
                        lambda payment: payment.payment_method_id == cash_payment_method).filtered(
                        lambda payment: payment.session_id.id == self.id and not payment.old_session_id).mapped('amount')
                    )
                    session.cash_register_total_entry_encoding = session.cash_register_id.total_entry_encoding + (
                        0.0 if session.state == 'closed' else total_cash_payment
                    )
                    session.cash_register_balance_end = session.cash_register_balance_start + session.cash_register_total_entry_encoding
                    session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
                else:
                    session.cash_register_total_entry_encoding = 0.0
                    session.cash_register_balance_end = 0.0
                    session.cash_register_difference = 0.0

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        for order in self.order_ids:
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            if not order.old_session_ids:
                for payment in order.payment_ids.filtered(
                        lambda payment: payment.session_id.id == self.id and not payment.old_session_id):
                    amount, date = payment.amount, payment.payment_date
                    if payment.payment_method_id.split_transactions:
                        if payment.payment_method_id.is_cash_count:
                            split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment],
                                                                                   {'amount': amount}, date)
                        else:
                            split_receivables[payment] = self._update_amounts(split_receivables[payment],
                                                                              {'amount': amount}, date)
                    else:
                        key = payment.payment_method_id
                        if payment.payment_method_id.is_cash_count:
                            combine_receivables_cash[key] = self._update_amounts(combine_receivables_cash[key],
                                                                                 {'amount': amount}, date)
                        else:
                            combine_receivables[key] = self._update_amounts(combine_receivables[key], {'amount': amount},
                                                                            date)

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id.property_account_receivable_id.id
                invoice_receivables[key] = self._update_amounts(invoice_receivables[key],
                                                                {'amount': order._get_amount_receivable()},
                                                                order.date_order)
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(
                        lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            elif order.partial_pay or order.reserved:
                if not order.old_session_ids:
                    self._create_partial_payment_debit(order, (order.amount_total - order.amount_paid))
                    order_taxes = defaultdict(tax_amounts)
                    for order_line in order.lines:
                        line = self._prepare_line(order_line)
                        # Combine sales/refund lines
                        sale_key = (
                            # account
                            line['income_account_id'],
                            # sign
                            -1 if line['amount'] < 0 else 1,
                            # for taxes
                            tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in
                                  line['taxes']),
                        )
                        sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']},
                                                               line['date_order'])
                        # Combine tax lines
                        for tax in line['taxes']:
                            tax_key = (
                                tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                            order_taxes[tax_key] = self._update_amounts(
                                order_taxes[tax_key],
                                {'amount': tax['amount'], 'base_amount': tax['base']},
                                tax['date_order'],
                                round=not rounded_globally
                            )
                    for tax_key, amounts in order_taxes.items():
                        if rounded_globally:
                            amounts = self._round_amounts(amounts)
                        for amount_key, amount in amounts.items():
                            taxes[tax_key][amount_key] += amount

                    if self.company_id.anglo_saxon_accounting:
                        # Combine stock lines
                        stock_moves = self.env['stock.move'].search([
                            ('picking_id', '=', order.picking_id.id),
                            ('company_id.anglo_saxon_accounting', '=', True),
                            ('product_id.categ_id.property_valuation', '=', 'real_time')
                        ])
                        for move in stock_moves:
                            exp_key = move.product_id.property_account_expense_id or move.product_id.categ_id.property_account_expense_categ_id
                            out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                            amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                            stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key],
                                                                          {'amount': amount}, move.picking_id.date)
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
                                                                         move.picking_id.date)
                # else:
                #     self.partial_paid_credit(order)
            else:
                if not order.old_session_ids:
                    order_taxes = defaultdict(tax_amounts)
                    for order_line in order.lines:
                        line = self._prepare_line(order_line)
                        # Combine sales/refund lines
                        sale_key = (
                            # account
                            line['income_account_id'],
                            # sign
                            -1 if line['amount'] < 0 else 1,
                            # for taxes
                            tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in
                                  line['taxes']),
                        )
                        sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']},
                                                               line['date_order'])
                        # Combine tax lines
                        for tax in line['taxes']:
                            tax_key = (
                                tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                            order_taxes[tax_key] = self._update_amounts(
                                order_taxes[tax_key],
                                {'amount': tax['amount'], 'base_amount': tax['base']},
                                tax['date_order'],
                                round=not rounded_globally
                            )
                    for tax_key, amounts in order_taxes.items():
                        if rounded_globally:
                            amounts = self._round_amounts(amounts)
                        for amount_key, amount in amounts.items():
                            taxes[tax_key][amount_key] += amount

                    if self.company_id.anglo_saxon_accounting:
                        # Combine stock lines
                        stock_moves = self.env['stock.move'].search([
                            ('picking_id', '=', order.picking_id.id),
                            ('company_id.anglo_saxon_accounting', '=', True),
                            ('product_id.categ_id.property_valuation', '=', 'real_time')
                        ])
                        for move in stock_moves:
                            exp_key = move.product_id.property_account_expense_id or move.product_id.categ_id.property_account_expense_categ_id
                            out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                            amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                            stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key],
                                                                          {'amount': amount},
                                                                          move.picking_id.date)
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
                                                                         move.picking_id.date)

                    # Increasing current partner's customer_rank
                    order.partner_id._increase_rank('customer_rank')
                # else:
                #     self.partial_paid_credit(order)

        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        data.update({
            'taxes': taxes,
            'sales': sales,
            'stock_expense': stock_expense,
            'split_receivables': split_receivables,
            'combine_receivables': combine_receivables,
            'split_receivables_cash': split_receivables_cash,
            'combine_receivables_cash': combine_receivables_cash,
            'invoice_receivables': invoice_receivables,
            'stock_output': stock_output,
            'order_account_move_receivable_lines': order_account_move_receivable_lines,
            'MoveLine': MoveLine
        })
        return data

    def partial_paid_credit(self, order):
        partial_payment_amount = {'amount': 0.0, 'amount_converted': 0.0}
        customer_income_account = order.partner_id.property_account_receivable_id.id
        partial_payment_amount_args = {
            'partner_id': order.partner_id.id,
            'move_id': self.move_id.id,
        }
        for payment in order.payment_ids.filtered(
                lambda payment: payment.session_id.id == self.id and not payment.old_session_id):
            partial_payment_amount['amount'] += payment.amount
        if not self.is_in_company_currency:
            partial_payment_amount['amount_converted'] = self.company_id.currency_id.round(
                partial_payment_amount['amount'])
        else:
            partial_payment_amount['amount_converted'] = partial_payment_amount['amount']
        partial_payment_amount_args['account_id'] = customer_income_account
        if partial_payment_amount['amount']:
            partial_payment_vals = [
                self._credit_amounts(partial_payment_amount_args, partial_payment_amount['amount'],
                                     partial_payment_amount['amount_converted'])
            ]
            self.env['account.move.line'].with_context(check_move_validity=False).create(partial_payment_vals)

    def _create_partial_payment_debit(self, order, amount):
        partial_payment_amount = {'amount': 0.0, 'amount_converted': 0.0}
        customer_income_account = order.partner_id.property_account_receivable_id.id
        partial_paid_args = {
            'partner_id': order.partner_id.id,
            'move_id': self.move_id.id,
        }
        partial_payment_amount['amount'] = amount
        if not self.is_in_company_currency:
            partial_payment_amount['amount_converted'] = self.company_id.currency_id.round(
                partial_payment_amount['amount'])
        else:
            partial_payment_amount['amount_converted'] = partial_payment_amount['amount']
        partial_paid_args['account_id'] = customer_income_account
        if partial_payment_amount['amount']:
            partial_paid_vals = [
                self._debit_amounts(partial_paid_args, partial_payment_amount['amount'],
                                    partial_payment_amount['amount_converted'])
            ]
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                partial_paid_vals)

    def _check_if_no_draft_orders(self):
        if not self.config_id.enable_order_reservation:
            super(PosSession, self)._check_if_no_draft_orders()
        else:
            return True

    @api.depends('order_ids.payment_ids.amount')
    def _compute_total_payments_amount(self):
        total_payments_amount = 0.0
        for session in self:
            for order in session.order_ids:
                for payment in order.payment_ids.filtered(lambda payment: not payment.old_session_id):
                    total_payments_amount += payment.amount
            session.total_payments_amount = total_payments_amount

    def _compute_order_count(self):
        for session in self:
            pos_order_count = 0
            for order in session.order_ids:
                if session.id == order.session_id.id:
                    if not order.old_session_ids:
                        pos_order_count += 1
            session.order_count = pos_order_count

    def action_view_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'tree'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('session_id', 'in', self.ids), ('old_session_ids', '=', False)],
        }

    def action_pos_session_open(self):
        pos_order = self.env['pos.order'].search([('state', '=', 'draft')])
        for order in pos_order:
            if order.session_id.state != 'opened':
                if self.config_id == order.config_id:
                    order.write({
                        # 'session_id': self.id,
                        'old_session_ids': [(4, order.session_id.id)],
                    })
                    for payment in order.payment_ids:
                        if not payment.old_session_id:
                            payment.write({'old_session_id': order.session_id.id})
        return super(PosSession, self).action_pos_session_open()


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.constrains('amount')
    def _check_amount(self):
        if not self._context.get('from_pos'):
            super(AccountBankStatementLine, self)._check_amount()

    @api.constrains('amount', 'amount_currency')
    def _check_amount_currency(self):
        if not self._context.get('from_pos'):
            super(AccountBankStatementLine, self)._check_amount_currency()


class res_partner(models.Model):
    _inherit = "res.partner"

    # @api.model_create_multi
    def _compute_remain_credit_limit(self):
        for partner in self:
            total_credited = 0
            orders = self.env['pos.order'].search([('partner_id', '=', partner.id),
                                                   ('state', '=', 'draft')])
            for order in orders:
                total_credited += order.amount_due
            partner.remaining_credit_limit = partner.credit_limit - total_credited

    remaining_credit_limit = fields.Float("Remaining Credit Limit", compute="_compute_remain_credit_limit")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
