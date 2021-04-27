odoo.define('bebepolis_core.screens', function (require) {
"use strict";

var screens = require('point_of_sale.screens');

screens.ClientListScreenWidget.include({
    init: function(parent, options){
        this._super(parent, options);
        this.integer_client_details.push('parent_id');
    },
    display_client_details: function(visibility,partner,clickpos){
        var self = this;
        var contents = this.$('.client-details-contents');
        contents.off('click','.button.new-address');
        contents.on('click', '.button.new-address', function(event){
            self.display_client_details('edit',{
                'name': partner.name,
                'country_id': partner.country_id,
                'state_id': partner.state_id,
                'parent_id': partner.id,
                'type': 'invoice',
            });
        });
        self._super(visibility,partner,clickpos);
    },
});

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