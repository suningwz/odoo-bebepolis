odoo.define('point_of_sale.ReservationModeButton', function(require) {
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
        mounted() {
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
        }
        willUnmount() {
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        async onClick() {
	        var order = this.env.pos.get_order();
	        order.set_reservation_mode(!order.get_reservation_mode());
	        order.get_reservation_mode() ? this.$el.addClass('highlight') : this.$el.removeClass('highlight')
        }
    }
    ReservationModeButton.template = 'ReservationMode';

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
