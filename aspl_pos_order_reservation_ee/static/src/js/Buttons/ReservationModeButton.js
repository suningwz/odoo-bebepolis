odoo.define('aspl_pos_order_reservation_ee.ReservationModeButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class ReservationModeButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        is_active(){
	        return this.env.pos.get_order().get_reservation_mode();
        }
        async onClick() {
	        var order = this.env.pos.get_order();
	        order.set_reservation_mode(!order.get_reservation_mode());
	        order.get_reservation_mode() ? this.$el.addClass('highlight') : this.$el.removeClass('highlight')
        }
    }
    ReservationModeButton.template = 'ReservationModeButton';

    ProductScreen.addControlButton({
        component: ReservationModeButton,
        condition: function() {
            return this.env.pos.config.enable_order_reservation;
        },
        position: ['before', 'SetPricelistButton'],
    });

    Registries.Component.add(ReservationModeButton);

    return ReservationModeButton;
});
