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
});