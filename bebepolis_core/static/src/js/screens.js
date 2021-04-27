odoo.define('bebepolis_core.screens', function (require) {
"use strict";

var screens = require('point_of_sale.screens');

var EditProductDescription = screens.ActionButtonWidget.extend({
    template : 'EditProductDescription',
    init: function(param, options) {
        var res = this._super(param, options);
        this.numpad_state = param.numpad.state;
        return res;
    },
    button_click : function() {
        var self = this;
        var order = self.pos.get_order();
        if(order.get_selected_orderline()){
            self.gui.show_popup("edit_product_description_popup");
        }
        return;
    },
});

screens.define_action_button({
    'name' : 'EditProductDescription',
    'widget' : EditProductDescription,
    'condition': function(){
        return true;
    },
});

return {
    'EditProductDescription': EditProductDescription
}

});