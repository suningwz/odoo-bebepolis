odoo.define('bebepolis_core.models', function (require) {
"use strict";

var models = require('point_of_sale.models');
var rpc = require('web.rpc');

var _super_pos_model = models.PosModel.prototype;

models.PosModel = models.PosModel.extend({
    load_server_data: function () {
        if (!this.models[1].model || (this.models[1].model && this.models[1].model != 'res.company')){
            throw new Error("res.company model not found");
        }
        this.models[1].fields.push('street', 'street2', 'city', 'zip');
        if (!this.models[4].model || (this.models[4].model && this.models[4].model != 'res.partner')){
            throw new Error("res.partner model not found");
        }
        this.models[4].fields.push('parent_id', 'type');
        return _super_pos_model.load_server_data.apply(this, arguments);
    },
});

var _super_order = models.Order.prototype;

models.Order = models.Order.extend({
    initialize: function(attributes,options){
        var self = this;
        var order_super = _super_order.initialize.apply(this, arguments);
        this.set({'note': false,});
        return order_super;
    },
    export_for_printing: function () {
        var result = _super_order.export_for_printing.apply(this, arguments);
        var company = this.pos.company;
        var order = this.pos.get_order();
        if (order.attributes && order.attributes.reservation_mode){
            result.reservation_mode = true;
            result.delivery_date = order.attributes.delivery_date;
            result.paying_due = order.attributes.paying_due;
            result.note = order.attributes.note;
        }
        result.company.company_address = company;
        result.order_uid = this.uid
        return result;
    },
    export_as_JSON: function() {
        var self = this;
        var new_val = {};
        var orders = _super_order.export_as_JSON.call(this);
        new_val = {
            note: self.get_observations() || false,
        }
        $.extend(orders, new_val);
        return orders;
    },
    get_observations: function () {
        return this.get('note');
    },
    set_observations: function (value) {
        this.set('note', value);
    },
});

var _super_order_line = models.Orderline.prototype;

models.Orderline = models.Orderline.extend({
    initialize: function(attr,options){
        var order_line_super = _super_order_line.initialize.apply(this, arguments);
        if (options.json) {
            this.set_product_description(options.json.product_description || '');
        }else{
            this.set_product_description(options.product.display_name);
        }
        return order_line_super;
    },
    set_product_description: function(description){
        this.product_description = description;
        this.trigger('change',this);
    },
    get_product_description: function(){
        return this.product_description;
    },
    export_as_JSON: function() {
        var order_line_super = _super_order_line.export_as_JSON.apply(this, arguments);
        order_line_super.product_description = this.get_product_description();
        return order_line_super;
    },
    export_for_printing: function(){
        var order_line_super = _super_order_line.export_for_printing.apply(this, arguments);
        order_line_super.product_description = this.get_product_description();
        return order_line_super;
    },
});
});