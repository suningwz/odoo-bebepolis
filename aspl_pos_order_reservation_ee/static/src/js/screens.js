odoo.define('aspl_pos_order_reservation_ee.screens', function (require) {
	var screens = require('point_of_sale.Screens');
	var { gui } = require('point_of_sale.Gui');
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var PopupWidget = require('point_of_sale.Popups');
	var models = require('point_of_sale.models');
	
	var core = require('web.core');
	var QWeb = core.qweb;
	var round_pr = utils.round_precision;
	var _t = core._t;
	
	var ShowOrderList = screens.ActionButtonWidget.extend({
	    template : 'ShowOrderList',
	    button_click : function() {
	        self = this;
	        self.gui.show_screen('orderlist');
	    },
	});

	screens.define_action_button({
	    'name' : 'showorderlist',
	    'widget' : ShowOrderList,
	    'condition': function(){
	        return this.pos.config.enable_order_reservation
	    },
	});
	
	var ReservationMode = screens.ActionButtonWidget.extend({
	    template : 'ReservationMode',
	    button_click : function() {
	        var self = this;
	        var order = self.pos.get_order();
	        order.set_reservation_mode(!order.get_reservation_mode());
	        order.get_reservation_mode() ? this.$el.addClass('highlight') : this.$el.removeClass('highlight')
	    },
	});

	screens.define_action_button({
	    'name' : 'ReservationMode',
	    'widget' : ReservationMode,
	    'condition': function(){
	        return this.pos.config.enable_order_reservation
	    },
	});

    var SaveDraftButton = screens.ActionButtonWidget.extend({
	    template : 'SaveDraftButton',
	    button_click : function() {
	        var self = this;
            var selectedOrder = this.pos.get_order();
            selectedOrder.initialize_validation_date();
            var currentOrderLines = selectedOrder.get_orderlines();
            var orderLines = [];
            var client = selectedOrder.get_client();
            _.each(currentOrderLines,function(item) {
                return orderLines.push(item.export_as_JSON());
            });
            if (orderLines.length === 0) {
                return alert ('Please select product !');
            } else {
            	if(!selectedOrder.get_client()){
            		self.gui.show_screen('clientlist');
            		return
            	}
                var credit = selectedOrder.get_total_with_tax() - selectedOrder.get_total_paid();
        		if (client && credit > client.remaining_credit_limit){
                    self.gui.show_popup('max_limit',{
                        remaining_credit_limit: client.remaining_credit_limit,
                        draft_order: true,
                    });
                    return
        	    } else {
                    this.pos.push_order(selectedOrder);
                    self.gui.show_screen('receipt');
                }
            }
	    },
	});

    screens.define_action_button({
	    'name' : 'savedraftbutton',
	    'widget' : SaveDraftButton,
	    'condition': function(){
	        return this.pos.config.allow_reservation_with_no_amount;
	    },
	});

    var ShowReservedItemsList = screens.ActionButtonWidget.extend({
	    template : 'ShowReservedItemsList',
	    button_click : function() {
	        self = this;
	        self.gui.show_screen('reserved_items_list');
	    },
	});

	screens.define_action_button({
	    'name' : 'ShowReservedItemsList',
	    'widget' : ShowReservedItemsList,
	    'condition': function(){
	        return this.pos.config.enable_order_reservation
	    },
	});

	/* Order list screen */
	var OrderListScreenWidget = screens.ScreenWidget.extend({
	    template: 'OrderListScreenWidget',

	    init: function(parent, options){
	    	var self = this;
	        this._super(parent, options);
	        this.reload_btn = function(){
	        	$('.fa-refresh').toggleClass('rotate', 'rotate-reset');
	        	if($('#select_draft_orders').prop('checked')){
            		$('#select_draft_orders').click();
            	}
	        	self.reloading_orders();
	        };
	        if(this.pos.config.iface_vkeyboard && self.chrome.widget.keyboard){
            	self.chrome.widget.keyboard.connect(this.$('.searchbox input'));
            }
	    },

	    events: {
	    	'click .button.back':  'click_back',
	    	'keyup .searchbox input': 'search_order',
	    	'click .searchbox .search-clear': 'clear_search',
	        'click .button.reserved':  'click_reserved',
	        'click .order-line td:not(.order_history_button)': 'click_order_line',
	        'click #pay_due_amt': 'pay_order_due',
	        'click #cancel_order': 'click_cancel_order',
	        'click #delivery_date': 'click_delivery_date',
	    },
	    filter:"all",
        date: "all",
        clear_cart: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var currentOrderLines = order.get_orderlines();
        	if(currentOrderLines && currentOrderLines.length > 0){
        		_.each(currentOrderLines,function(item) {
        			order.remove_orderline(item);
                });
        	} else {
        		return
        	}
        	self.clear_cart();
        },
        get_orders: function(){
        	return this.pos.get('pos_order_list');
        },
        click_back: function(){
        	this.gui.show_screen('products');
        },
        search_order: function(event){
        	var self = this;
        	var search_timeout = null;
        	$(event.currentTarget).autocomplete({
                source: self.search_list,
                select: function (a, b) {
                    self.perform_search(b.item.value, true);
                }
            });
            clearTimeout(search_timeout);
            var query = $(event.currentTarget).val();
            search_timeout = setTimeout(function(){
                self.perform_search(query, event.which === 13);
            },70);
	    },
	    click_reserved: function(event){
	    	var self = this;
        	if($(event.currentTarget).hasClass('selected')){
        		$(event.currentTarget).removeClass('selected');
        		self.filter = "all";
    		}else{
    			$(event.currentTarget).addClass('selected');
        		self.filter = "reserved";
    		}
    		self.render_list(self.get_orders());
	    },
	    click_order_line: function(event){
	    	var self = this;
	    	var order_id = parseInt($(event.currentTarget).parent().data('id'));
	    	if(order_id){
	    		self.gui.show_screen('orderdetail', {'order_id': order_id});
	    	}
	    },
	    click_cancel_order: function(event){
	    	var self = this;
	    	var order_id = parseInt($(event.currentTarget).data('id'));
            var result_order = self.pos.db.get_order_by_id(order_id);
            if(result_order){
                self.get_data_for_selected_order(result_order).then(function(result){
                    self.gui.show_popup("cancel_order_popup", {
                        'lines': result[0].lines ,
                        'order_tobe_cancel': result_order,
                        'pack_lots_by_line': result[0].pack_lots_by_line,
                        'pack_lots': result[0].pack_lots,
                        'line':result[0].line,
                        'quantity_by_lot':result[0].quantity_dict,
                        'product_by_quantity':result[0].product_by_quantity,
                    });
                });
            }
	    },
	    get_data_for_selected_order : function(order){
	        var self = this;
	        var fields = self.fieldNames
            return new Promise(function (resolve, reject) {
                var params = {
                    model: 'pos.order.line',
                    method: 'get_order_line_data',
                    fields: self.fieldNames,
                    args:[fields,_.pluck(order.lines, 'id')]
                }
                rpc.query(params, {
                    timeout: 3000,
                    shadow: true,
                })
                .then(function (records) {
                    if (records && records.length > 0) { // check if the partners we got were real updates
                        resolve(records);
                    } else {
                        reject();
                    }
                }, function (type, err) { reject(); });
            });
	    },
	    click_delivery_date: function(event){
	    	var self = this;
	    	var order = self.pos.get_order();
            var order_id = parseInt($(event.currentTarget).data('id'));
            var result = self.pos.db.get_order_by_id(order_id);
            if(result){
	            order.set_delivery_date(result.delivery_date);
	            self.gui.show_popup("delivery_date_popup", { 'order': result, 'new_date': false });
            }
	    },
	    pay_order_due: function(event, order_id){
	        var self = this;
	        var order_id = event ? parseInt($(event.currentTarget).data('id')) : order_id;
	        var result = self.pos.db.get_order_by_id(order_id);
	        if(!result){
	        	var params = {
                	model: 'pos.order',
                	method: 'ac_pos_search_read',
                	args: [{ 'domain': [['id', '=', order_id], ['state', 'not in', ['draft']]] }],
                	fields: ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved', 'write_date', 'id', 'partner_id','lines','delivery_date','amount_total','amount_due','order_status'],
                }
	        	rpc.query(params, {async: false})
	            .then(function(order){
	                if(order && order[0]){
	                    result = order[0]
	                }
	            });
	        }
            if(result.state == "paid"){
                alert("Sorry, This order is paid State");
                return
            }
            if(result.state == "done"){
                alert("Sorry, This Order is Done State");
                return
            }
            if (result && result.lines.length > 0) {
                var count = 0;
                var selectedOrder = self.pos.get_order();
                var currentOrderLines = selectedOrder.get_orderlines();
                self.clear_cart();
                if (result.partner_id && result.partner_id[0]) {
                    var partner = self.pos.db.get_partner_by_id(result.partner_id[0])
                    if(partner){
                    	selectedOrder.set_client(partner);
                    }
                }
                if(!result.partial_pay && result.reserved){
                    selectedOrder.set_reservation_mode(true);
                }
                if(!result.reserved){
                    selectedOrder.set_partial_pay(true);
                }
                selectedOrder.set_delivery_date(result.delivery_date);
                selectedOrder.set_pos_reference(result.pos_reference);
                selectedOrder.set_paying_due(true);
                if (result.lines) {
                    var params = {
                        model: 'pos.order.line',
                        method: 'get_order_line_data',
                        args: [self.fieldNames, _.pluck(result.lines, 'id')]
                    }
                    rpc.query(params, {async: false})
                    .then(function(results) {
                        if(results){
                            _.each(results[0].line_search_read, function(res) {
                                var product = self.pos.db.get_product_by_id(Number(res.product_id[0]));
                                if(product){
                                    var line = new models.Orderline({}, {pos: self.pos, order: selectedOrder, product: product});
                                    line.set_discount(res.discount);
                                    line.set_line_status(res.line_status);
                                    var line = new models.Orderline({}, {pos: self.pos, order: selectedOrder, product: product});
                                    line.set_cancel_process(res.order_id);
                                    line.set_cancel_item(res.cancel_item);
                                    line.set_cancel_item_id(res.id);
                                    line.set_picking_id(res.picking_id[0]);
                                    if(product.type != "service"){
                                        if(res.qty == 0){
                                            var temp_qty = res.price_subtotal_incl / res.price_unit;
                                            line.set_quantity(temp_qty);
                                        }else{
                                            line.set_quantity(res.qty);
                                        }
                                    }
                                    if(product.tracking == 'lot'){
                                        var lot_name = results[0].pack_lots_by_line[res.id][0].lot_name
                                        var pack_lot_lines =  line.compute_lot_lines();
                                        if(pack_lot_lines.length === 0){
                                            line.pack_lot_lines.add(new models.Packlotline({}, {'order_line': line}));
                                            line.set_quantity_by_lot(pack_lot_lines)
                                        }
                                        line.pack_lot_lines.models[0].attributes.lot_name = lot_name
                                    }
                                    if(product.tracking == 'serial'){
                                        var pack_lot_lines =  line.compute_lot_lines();
                                        _.each(results[0].pack_lots_by_line[res.id],function(lot_line,index){
                                            line.pack_lot_lines.models[index].attributes.lot_name = lot_line.lot_name
                                        });
                                    }
                                    line.set_unit_price(res.price_unit);
                                    selectedOrder.add_orderline(line);
                                    selectedOrder.select_orderline(selectedOrder.get_last_orderline());
                                 }
                             });

                            var prd = self.pos.db.get_product_by_id(self.pos.config.prod_for_payment[0]);
                            if(prd && result.amount_due > 0){
                                var paid_amt = result.amount_total - result.amount_due;
                                selectedOrder.set_amount_paid(paid_amt);
                                selectedOrder.add_product(prd,{'quantity': -1, 'price': paid_amt});
                            }
                            self.gui.show_screen('payment');
                         }
                    });
                    selectedOrder.set_order_id(order_id);
                }
                selectedOrder.set_sequence(result.name);
            }
	    },
	    show: function(){
	    	var self = this;
	        this._super();
	        this.reload_orders();
	        $('input#datepicker').datepicker({
           	    dateFormat: 'yy-mm-dd',
                autoclose: true,
                closeText: 'Clear',
                showButtonPanel: true,
                onSelect: function (dateText, inst) {
                	var date = $(this).val();
					if (date){
					    self.date = date;
					    self.render_list(self.get_orders());
					}
				},
				onClose: function(dateText, inst){
                    if( !dateText ){
                        self.date = "all";
                        self.render_list(self.get_orders());
                    }
                }
            }).focus(function(){
                var thisCalendar = $(this);
                $('.ui-datepicker-close').click(function() {
                    thisCalendar.val('');
                    self.date = "all";
                    self.render_list(self.get_orders());
                });
            })
	        $('.button.reserved').removeClass('selected').trigger('click');
	    },
	    perform_search: function(query, associate_result){
	        var self = this;
            if(query){
				var orders = this.pos.db.search_order(query);
				self.render_list(orders);
            }else{
                this.render_list(self.get_orders());
            }
        },
        clear_search: function(){
            this.render_list(this.get_orders());
            this.$('.searchbox input')[0].value = '';
            this.$('.searchbox input').focus();
        },
	    render_list: function(orders){
	    	if(orders.length > 0){
	        	var self = this;
	            var contents = this.$el[0].querySelector('.order-list-contents');
	            contents.innerHTML = "";
	            var temp = [];
	            if(self.filter !== "" && self.filter !== "all"){
		            orders = $.grep(orders,function(order){
		            	return order.reserved;
		            });
	            }
	            if(self.date !== "" && self.date !== "all"){
	            	var x = [];
	            	for (var i=0; i<orders.length;i++){
	                    var date_order = $.datepicker.formatDate("yy-mm-dd",new Date(orders[i].date_order));
	            		if(self.date === date_order){
	            			x.push(orders[i]);
	            		}
	            	}
	            	orders = x;
	            }
	            for(var i = 0, len = Math.min(orders.length,1000); i < len; i++){
	                var order    = orders[i];
	                order.amount_total = parseFloat(order.amount_total).toFixed(2); 
                    	var clientline_html = QWeb.render('OrderlistLine',{widget: this, order:order});
	                var clientline = document.createElement('tbody');
	                clientline.innerHTML = clientline_html;
	                clientline = clientline.childNodes[1];
	                contents.appendChild(clientline);
	            }
	            $("table.order-list").simplePagination({
                    previousButtonClass: "btn btn-danger",
                    nextButtonClass: "btn btn-danger",
                    previousButtonText: '<i class="fa fa-angle-left fa-lg"></i>',
                    nextButtonText: '<i class="fa fa-angle-right fa-lg"></i>',
                    perPage:self.pos.config.record_per_page > 0 ? self.pos.config.record_per_page : 10
                });
            }
        },
        reload_orders: function(){
        	var self = this;
            var orders = self.get_orders()
            this.search_list = []
            _.each(self.pos.partners, function(partner){
                if(partner.name){
                    self.search_list.push(partner.name);
                }
            });
            _.each(orders, function(order){
                if(order.display_name){
                    self.search_list.push(order.display_name)
                }
                if(order.pos_reference){
                    self.search_list.push(order.pos_reference)
                }
            });
            this.render_list(orders);
        },
	    reloading_orders: function(){
	    	var self = this;
	    	var params = {
	    		model: 'pos.order',
	    		method: 'ac_pos_search_read',
	    		args: [{'domain': self.pos.domain_order}],
	    		fields: ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved', 'write_date', 'id', 'partner_id','lines','delivery_date','amount_total','amount_due','order_status'],
	    	}
	    	return rpc.query(params, {async: false})
	    	.then(function(result){
	    		self.pos.db.add_orders(result);
	    		self.pos.set({ 'pos_order_list' : result });
	    		self.reload_orders();
	    		return self.pos.get('pos_order_list');
	    	}).catch(function (error){
                if(error.code === 200 ){    // Business Logic Error, not a connection problem
                    self.gui.show_popup('error-traceback',{
                         'title': error.data.message,
                         'body':  error.data.debug
                    });
                 }
             });
	    },
	    renderElement: function(){
	    	var self = this;
	    	self._super();
	    	self.el.querySelector('.button.reload').addEventListener('click', this.reload_btn);
	    },
	});
	gui.define_screen({name:'orderlist', widget: OrderListScreenWidget});
	
	screens.PaymentScreenWidget.include({
        partial_payment: function() {
            var self = this;
            var currentOrder = this.pos.get_order();
            var client = currentOrder.get_client() || false;

            if(currentOrder.get_total_with_tax() > 0 && currentOrder.get_due() != 0){
				if(currentOrder.get_total_with_tax() > currentOrder.get_total_paid()
        			&& currentOrder.get_total_paid() != 0){
					var credit = currentOrder.get_total_with_tax() - currentOrder.get_total_paid();
					if (client && credit > client.remaining_credit_limit && !currentOrder.get_paying_due() && !currentOrder.get_cancel_order()){
						self.gui.show_popup('max_limit',{
							remaining_credit_limit: client.remaining_credit_limit,
							payment_obj: self,
						});
						return
					}
        	    }
            	if(currentOrder.get_reservation_mode() && !currentOrder.get_paying_due() && !currentOrder.get_cancel_order() && self.pos.config.enable_pos_welcome_mail){
            		currentOrder.set_fresh_order(true);
            	}
            	if(!currentOrder.get_reservation_mode()){
            	    currentOrder.set_partial_pay(true);
            	} else {
            	    currentOrder.set_draft_order(true);
            	}
				if(!currentOrder.get_delivery_date()){
					self.gui.show_popup("delivery_date_popup", { 'payment_obj': self, 'new_date': true });
				} else {
					if(currentOrder.get_total_paid() != 0){
						this.finalize_validation();
					}
					$('.js_reservation_mode').removeClass('highlight');
				}
        	}
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$('#partial_pay').click(function(){
            	if(self.pos.get_order().get_client()){
            	    if (self.pos.get_order().is_to_invoice()) {
            	        self.click_invoice();
            	    }
                	self.partial_payment();
                } else {
                	self.gui.show_screen('clientlist');
                }
            });
        },
        order_changes: function(){
            var self = this;
            this._super();
            var order = this.pos.get_order();
            var total = order ? order.get_total_with_tax() : 0;
            if(!order){
            	return
            } else if(order.get_due() == total || order.get_due() == 0){
            	self.$('#partial_pay').removeClass('highlight');
            } else {
            	self.$('#partial_pay').addClass('highlight');
            }
        },
        validate_order: function(force_validation){
        	this.pos.get_order().set_reservation_mode(false);
        	this._super(force_validation);
        },
        show: function(){
            var self = this;
            self._super();
            var order = self.pos.get_order();
            if(order.get_reservation_mode()){
                self.$('#partial_pay').show();
            } else {
                self.$('#partial_pay').text("Partial Pay");
            }
            if(order.get_total_with_tax() > 0){
                if((order.get_paying_due() || order.get_cancel_order())){
                    self.$('#partial_pay, .next').show();
                }
            } else {
                self.$('#partial_pay').hide();
                self.$('.next').show();
            }
            if((order.get_paying_due() || order.get_cancel_order())){
                self.$('#partial_pay').text("Pay");
            }
        },
        click_back: function(){
	        var self = this;
	        var order = this.pos.get_order();
	        if(order.get_paying_due() || order.get_cancel_order()){
                this.gui.show_popup('confirm',{
                    title: _t('Discard Sale Order'),
                    body:  _t('Do you want to discard the payment of POS '+ order.get_pos_reference() +' ?'),
                    confirm: function() {
                        order.finalize();
                    },
                });
            } else {
                self._super();
            }
        },
        click_invoice: function(){
            var order = this.pos.get_order();
            if(order.get_partial_pay() || order.get_cancel_order() || order.get_paying_due()){
                return
            }
            this._super();
        },
        click_set_customer: function(){
            var order = this.pos.get_order();
            if(order.get_cancel_order() || order.get_paying_due()){
                return
            }
            this._super();
        },
    });

    var OrderDetailScreenWidget = screens.ScreenWidget.extend({
        template: 'OrderDetailScreenWidget',
         init: function(parent, options){
            var self = this;
            self._super(parent, options);
        },
        show: function(){
            var self = this;
            self._super();

            var order = self.pos.get_order();
            var params = order.get_screen_data('params');
            var order_id = false;
            if(params){
                order_id = params.order_id;
            }
            if(order_id){
                self.clicked_order = self.pos.db.get_order_by_id(order_id)
            }
            this.renderElement();
            this.$('.back').click(function(){
                self.gui.back();
                if(params.previous){
                    self.pos.get_order().set_screen_data('previous-screen', params.previous);
                    if(params.partner_id){
                        $('.client-list-contents').find('.client-line[data-id="'+ params.partner_id +'"]').click();
                        $('#show_client_history').click();
                    }
                }

            });
            if(self.clicked_order){
				this.$('.pay').click(function(){
                    self.pos.gui.screen_instances.orderlist.pay_order_due(false, order_id)
                });
				var contents = this.$('.order-details-contents');
				contents.append($(QWeb.render('OrderDetails',{widget:this, order:self.clicked_order})));
				var params = {
					model: 'pos.payment',
					method: 'search_read',
					domain: [['pos_order_id', '=', order_id]],
					fields: ['payment_method_id','create_date','amount'],
				}
				rpc.query(params, {async: false})
				.then(function(statements){
					if(statements){
						self.render_list(statements);
					}
				});
            }

        },
        render_list: function(statements){
            var contents = this.$el[0].querySelector('.paymentline-list-contents');
            contents.innerHTML = "";
            for(var i = 0, len = Math.min(statements.length,1000); i < len; i++){
                var statement = statements[i];
                var paymentline_html = QWeb.render('PaymentLines',{widget: this, statement:statement});
                var paymentline = document.createElement('tbody');
                paymentline.innerHTML = paymentline_html;
                paymentline = paymentline.childNodes[1];
                contents.append(paymentline);
            }

        },
	});
	gui.define_screen({name:'orderdetail', widget: OrderDetailScreenWidget});

    screens.ClientListScreenWidget.include({
        show: function(){
            var self = this;
            this._super();
            var $show_customers = $('#show_customers');
            var $show_client_history = $('#show_client_history');
            if (this.pos.get_order().get_client() || this.new_client) {
                $show_client_history.removeClass('oe_hidden');
            }
            $show_customers.off().on('click', function(e){
                $('.client-list').removeClass('oe_hidden');
                $('#customer_history').addClass('oe_hidden')
                $show_customers.addClass('oe_hidden');
                $show_client_history.removeClass('oe_hidden');
            })
        },
        toggle_save_button: function(){
            var self = this;
            this._super();
            var $show_customers = this.$('#show_customers');
            var $show_client_history = this.$('#show_client_history');
            var $customer_history = this.$('#customer_history');
            var client = this.new_client || this.pos.get_order().get_client();
            if (this.editing_client) {
                $show_customers.addClass('oe_hidden');
                $show_client_history.addClass('oe_hidden');
            } else {
                if(client){
                    $show_client_history.removeClass('oe_hidden');
                    $show_client_history.off().on('click', function(e){
                        self.render_client_history(client);
                        $('.client-list').addClass('oe_hidden');
                        $customer_history.removeClass('oe_hidden');
                        $show_client_history.addClass('oe_hidden');
                        $show_customers.removeClass('oe_hidden');
                    });
                } else {
                    $show_client_history.addClass('oe_hidden');
                    $show_client_history.off();
                }
            }
        },
        _get_customer_history: function(partner){

            return new Promise(function (resolve, reject) {
                var params = {
                    model: 'pos.order',
                    method: 'search_read',
                    fields: ['create_date', 'state', 'date_order', 'name', 'pos_reference', 'reserved', 'write_date', 'id', 'partner_id','amount_total','amount_paid', 'name', 'amount_due','order_status'],
                }
                rpc.query(params, {
                    timeout: 3000,
                    shadow: true,
                })
                .then(function (orders) {
                    if(orders){
                         resolve(orders);
                    }else{
                        reject();
                    }
                }, function (type, err) { reject(); });
            })

        },
        render_client_history: function(partner){
            var self = this;
            var contents = this.$el[0].querySelector('#client_history_contents');
            contents.innerHTML = "";
            self._get_customer_history(partner).then(function (orders) {
                 var filtered_orders = orders.filter(function(o){return ((o.amount_total - o.amount_paid) > 0 && o.partner_id[0] == partner.id)})
                 partner['history'] = filtered_orders;
                if(partner.history){
                    for (var i=0; i < partner.history.length; i++){
                        var history = partner.history[i];
                        var history_line_html = QWeb.render('ClientHistoryLine', {
                            partner: partner,
                            order: history,
                            widget: self,
                        });
                        var history_line = document.createElement('tbody');
                        history_line.innerHTML = history_line_html;
                        history_line = history_line.childNodes[1];
                        history_line.addEventListener('click', function(e){
                            var order_id = $(this).data('id');
                            if(order_id){
                                var previous = self.pos.get_order().get_screen_data('previous-screen');
                                self.gui.show_screen('orderdetail', {
                                    order_id: order_id,
                                    previous: previous,
                                    partner_id: partner.id
                                });
                            }
                        })
                        contents.appendChild(history_line);
                    }
                }
            });

        },
        render_payment_history: function(){
            var self = this;
            var $client_details_box = $('.client-details-box');
            $client_details_box.addClass('oe_hidden');
        }
	});

    var ReservedItemListScreenWidget = screens.ScreenWidget.extend({
	    template: 'ReservedItemListScreenWidget',
	    events: {
	    	'click .button.back': 'click_back',
	    	'keyup .searchbox input': 'search_order',
	    	'click .searchbox .search-clear': 'clear_search',
	    },
	    click_back: function(){
	    	this.gui.back();
	    },
	    start: function(){
	    	var self = this;
	    	this._super();
	    	self.pos.db.add_reserved_items(self._get_only_lines());
	    },
	    show: function(){
	    	var self = this;
	    	this._super();
	    	this.render_list(this._get_only_lines())
	    },
	    _get_only_lines: function(){
	    	var self = this;
	    	var orders = this.pos.get('pos_order_list');
	    	var only_lines = []
	    	orders = _.where(orders, {reserved: true})
	    	_.each(orders, function(order){
	    		_.each(order.lines, function(line){
	    			if(!line.cancel_item && line.line_status != "full"){
	    				only_lines.push(line);
	    			}
	    		})
	    	})
	    	return only_lines
	    	
	    },
	    render_list: function(lines){
	    	var self = this;
	    	var contents = this.$el[0].querySelector('.reserved-item-list-contents');
            contents.innerHTML = "";
	    	_.each(lines, function(line){
	    		var order = self.pos.db.get_order_by_id(line.order_id[0]);
	    		var reserved_item_html = QWeb.render('ReservedItemlistLine',{widget: this, order:order, line: line});
	    		var itemline = document.createElement('tbody');
	    		itemline.innerHTML = reserved_item_html;
	    		itemline = itemline.childNodes[1];
	    		contents.appendChild(itemline);
	    	});
	    	$("table.reserved-item-list").simplePagination({
				previousButtonClass: "btn btn-danger",
				nextButtonClass: "btn btn-danger",
				previousButtonText: '<i class="fa fa-angle-left fa-lg"></i>',
				nextButtonText: '<i class="fa fa-angle-right fa-lg"></i>',
				perPage:10
			});
	    },
	    search_order: function(event){
        	var self = this;
        	var search_timeout = null;
            clearTimeout(search_timeout);
            var query = $(event.currentTarget).val();
            search_timeout = setTimeout(function(){
                self.perform_search(query, event.which === 13);
            },70);
	    },
	    perform_search: function(query, associate_result){
	        var self = this;
            if(query){
				var lines = this.pos.db.search_item(query);
				self.render_list(lines);
            }else{
                this.render_list(this._get_only_lines())
            }
        },
        clear_search: function(){
        	this.render_list(this._get_only_lines())
            this.$('.searchbox input')[0].value = '';
            this.$('.searchbox input').focus();
        },
    });
    gui.define_screen({name:'reserved_items_list', widget: ReservedItemListScreenWidget});
});
