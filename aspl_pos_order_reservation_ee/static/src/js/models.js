odoo.define('aspl_pos_order_reservation_ee.models', function (require) {
	var models = require('point_of_sale.models');
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var round_pr = utils.round_precision;

    models.load_fields("res.partner", ['remaining_credit_limit', 'credit_limit']);
    models.load_fields("pos.order", ['payment_ids']);

	var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            var self = this;
            var order_super = _super_Order.initialize.apply(this, arguments);
            this.set({
                'reservation_mode': false,
                'delivery_date': false,
                'draft_order': false,
                'paying_due': false,
                'fresh_order': false,
            })
            this.remaining_amount = 0.00;
            this.amount_due = 0.00;
            $('.js_reservation_mode').removeClass('highlight');
            return order_super;
        },
        generate_unique_id: function() {
            var timestamp = new Date().getTime();
            return Number(timestamp.toString().slice(-10));
        },
        // Order History
        set_sequence:function(sequence){
        	this.set('sequence',sequence);
        },
        get_sequence:function(){
        	return this.get('sequence');
        },
        set_order_id: function(order_id){
            this.set('order_id', order_id);
        },
        get_order_id: function(){
            return this.get('order_id');
        },
        set_amount_paid: function(amount_paid) {
            this.set('amount_paid', amount_paid);
        },
        get_amount_paid: function() {
            return this.get('amount_paid');
        },
        set_amount_return: function(amount_return) {
            this.set('amount_return', amount_return);
        },
        get_amount_return: function() {
            return this.get('amount_return');
        },
        set_amount_tax: function(amount_tax) {
            this.set('amount_tax', amount_tax);
        },
        get_amount_tax: function() {
            return this.get('amount_tax');
        },
        set_amount_total: function(amount_total) {
            this.set('amount_total', amount_total);
        },
        get_amount_total: function() {
            return this.get('amount_total');
        },
        set_company_id: function(company_id) {
            this.set('company_id', company_id);
        },
        get_company_id: function() {
            return this.get('company_id');
        },
        set_date_order: function(date_order) {
            this.set('date_order', date_order);
        },
        get_date_order: function() {
            return this.get('date_order');
        },
        set_pos_reference: function(pos_reference) {
            this.set('pos_reference', pos_reference)
        },
        get_pos_reference: function() {
            return this.get('pos_reference')
        },
        set_user_name: function(user_id) {
            this.set('user_id', user_id);
        },
        get_user_name: function() {
            return this.get('user_id');
        },
        set_journal: function(statement_ids) {
            this.set('statement_ids', statement_ids)
        },
        get_journal: function() {
            return this.get('statement_ids');
        },
        get_change: function(paymentline) {
            if (!paymentline) {
                if(this.get_total_paid() > 0 || this.get_cancel_order()){
                    var change = this.get_total_paid() - this.get_total_with_tax();
                }else{
                    var change = this.get_amount_return();
                }
            } else {
                var change = -this.get_total_with_tax(); 
                var lines  = this.pos.get_order().get_paymentlines();
                for (var i = 0; i < lines.length; i++) {
                    change += lines[i].get_amount();
                    if (lines[i] === paymentline) {
                        break;
                    }
                }
            }
            return round_pr(Math.max(0,change), this.pos.currency.rounding);
        },
        get_total_with_tax: function() {
            var total = _super_Order.get_total_with_tax.call(this);
            return (total + this.remaining_amount);
        },
        set_remaining_amount: function(amount){
            this.remaining_amount = amount;
        },
        get_remaining_amount: function(amount){
            return this.remaining_amount;
        },
        export_as_JSON: function() {
            var self = this;
        	var new_val = {};
            var orders = _super_Order.export_as_JSON.call(this);
            var cancel_orders = '';
            _.each(self.get_orderlines(), function(line){
                if(line.get_cancel_item()){
                    cancel_orders += " "+line.get_cancel_item();
                }
            });
            new_val = {
                old_order_id: this.get_order_id(),
                sequence: this.get_sequence(),
                pos_reference: this.get_pos_reference(),
                amount_due: this.get_due() ? this.get_due() : 0.00,
                reserved: this.get_reservation_mode() || false,
                delivery_date: this.get_delivery_date() || false,
                cancel_order_ref: cancel_orders || false,
                cancel_order: this.get_cancel_order() || false,
                set_as_draft: this.get_draft_order() || false,
                customer_email: this.get_client() ? this.get_client().email : false,
                fresh_order: this.get_fresh_order() || false,
                partial_pay: this.get_partial_pay() || false,
                pos_session_id: this.pos.pos_session.id,
            }
            $.extend(orders, new_val);
            return orders;
        },
        export_for_printing: function(){
            var self = this;
            var orders = _super_Order.export_for_printing.call(this);
            var last_paid_amt = 0;
            var currentOrderLines = this.get_orderlines();
            if(currentOrderLines.length > 0) {
            	_.each(currentOrderLines,function(item) {
            		if(self.pos.config.enable_partial_payment &&
            				item.get_product().id == self.pos.config.prod_for_payment[0] ){
            			last_paid_amt = item.get_display_price()
            		}
                });
            }
            var total_paid_amt = this.get_total_paid()-last_paid_amt
            var new_val = {
            	reprint_payment: this.get_journal() || false,
            	ref: this.get_pos_reference() || false,
            	date_order: this.get_date_order() || false,
            	last_paid_amt: last_paid_amt || 0,
            	total_paid_amt: total_paid_amt || false,
            	amount_due: this.get_due() ? this.get_due() : 0.00,
            	old_order_id: this.get_order_id(),
            	delivery_date: moment(this.get_delivery_date()).format('L') || false,
            };
            $.extend(orders, new_val);
            return orders;
        },
        set_date_order: function(val){
        	this.set('date_order',val)
        },
        get_date_order: function(){
        	return this.get('date_order')
        },
        set_reservation_mode: function(mode){
            this.set('reservation_mode', mode)
        },
        get_reservation_mode: function(){
            return this.get('reservation_mode');
        },
        set_delivery_date: function(val){
            this.set('delivery_date', val)
        },
        get_delivery_date: function(){
            return this.get('delivery_date');
        },
        set_cancel_order: function(val){
            this.set('cancel_order', val)
        },
        get_cancel_order: function(){
            return this.get('cancel_order');
        },
        set_paying_due: function(val){
            this.set('paying_due', val)
        },
        get_paying_due: function(){
            return this.get('paying_due');
        },
        set_draft_order: function(val) {
            this.set('draft_order', val);
        },
        get_draft_order: function() {
            return this.get('draft_order');
        },
        set_cancellation_charges: function(val) {
            this.set('cancellation_charges', val);
        },
        get_cancellation_charges: function() {
            return this.get('cancellation_charges');
        },
        set_refund_amount: function(refund_amount) {
            this.set('refund_amount', refund_amount);
        },
        get_refund_amount: function() {
            return this.get('refund_amount');
        },
        set_fresh_order: function(fresh_order) {
            this.set('fresh_order', fresh_order);
        },
        get_fresh_order: function() {
            return this.get('fresh_order');
        },
        set_partial_pay: function(partial_pay) {
            this.set('partial_pay', partial_pay);
        },
        get_partial_pay: function() {
            return this.get('partial_pay');
        },
    });
    
    var _super_posmodel = models.PosModel;
    models.PosModel = models.PosModel.extend({
        load_server_data: function(){
            var self = this;
            var loaded = _super_posmodel.prototype.load_server_data.call(this);
            loaded = loaded.then(function(){
                var date = new Date();
                var domain;
                var start_date;
                self.domain_order = []
                if(date){
                    if(self.config.last_days){
                        date.setDate(date.getDate() - self.config.last_days);
                    }
                    start_date = date.toJSON().slice(0,10);
                    self.domain_order.push(['create_date' ,'>=', start_date]);
                }
                self.domain_order.push(['state','in',['draft']])
                var params = {
                    model: 'pos.order',
                    method: 'ac_pos_search_read',
                    args: [{'domain': self.domain_order}],
                    fields: ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved', 'write_date', 'id', 'partner_id','lines','delivery_date','amount_total','amount_due','order_status'],
                }
                return rpc.query(params, {async: false})
                .then(function(orders){
                    self.db.add_orders(orders);
                    self.set({'pos_order_list' : orders});
                });
            });
            return loaded;
        },
        _save_to_server: function (orders, options) {
            var self = this;
            return _super_posmodel.prototype._save_to_server.apply(this, arguments)
            .then(function(server_ids){
                if(server_ids.length > 0 && self.config.enable_order_reservation){
                    var server_id_list = [];
                    _.each(server_ids, function(each_data){
                        if(each_data && each_data.id){
                            server_id_list.push(each_data.id)
                        }
                    });
                    var params = {
                        model: 'pos.order',
                        method: 'ac_pos_search_read',
                        args: [{'domain': [['id', 'in', server_id_list]]}],
                        fields: ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved', 'write_date', 'id', 'partner_id','lines','delivery_date','amount_total','amount_due','order_status'],
                    }
                    rpc.query(params, {async: false}).then(function(orders){
                        if(orders.length > 0){
                            orders = orders[0];
                            var exist_order = _.findWhere(self.get('pos_order_list'), {'pos_reference': orders.pos_reference})
                            if(exist_order){
                                _.extend(exist_order, orders);
                            } else {
                                self.get('pos_order_list').push(orders);
                            }
                            var new_orders = _.sortBy(self.get('pos_order_list'), 'id').reverse();
                            self.db.add_orders(new_orders);
                            self.set({ 'pos_order_list' : new_orders });
                        }
                    });
                }
            });
        },
    });

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            this.cancel_item = false;
            this.consider_qty = 0;
            _super_orderline.initialize.call(this, attr, options);
        },
        set_cancel_item: function(val){
            this.set('cancel_item', val)
        },
        get_cancel_item: function(){
            return this.get('cancel_item');
        },
        set_consider_qty: function(val){
            this.set('consider_qty', val)
        },
        get_consider_qty: function(){
            return this.get('consider_qty');
        },
        set_picking_id: function(picking_id){
            this.set('picking_id', picking_id)
        },
        get_picking_id: function(){
            return this.get('picking_id');
        },
        export_as_JSON: function() {
            var self = this;
            var loaded = _super_orderline.export_as_JSON.call(this);
            loaded.cancel_item = self.get_cancel_item() || false;
            loaded.cancel_process = self.get_cancel_process() || false;
            loaded.cancel_qty = self.get_quantity() || false;
            loaded.consider_qty = self.get_consider_qty();
            loaded.cancel_item_id = self.get_cancel_item_id() || false;
            loaded.line_status = self.get_line_status() || false;
            loaded.picking_id = self.get_picking_id() || false;
            return loaded;
        },
        set_cancel_process: function(oid) {
            this.set('cancel_process', oid)
        },
        get_cancel_process: function() {
            return this.get('cancel_process');
        },
        set_cancel_item_id: function(val) {
            this.set('cancel_item_id', val)
        },
        get_cancel_item_id: function() {
            return this.get('cancel_item_id');
        },
        set_line_status: function(val) {
            this.set('line_status', val)
        },
        get_line_status: function() {
            return this.get('line_status');
        },
    });

})
