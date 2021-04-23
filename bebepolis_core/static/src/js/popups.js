odoo.define('bebepolis_core.popups', function (require) {
"use strict";

var DeliveryDatePopup = require('aspl_pos_order_reservation_ee.popups').DeliveryDatePopup;

DeliveryDatePopup.include({
    _onKeyupDeliveryNote: function(event){
        event.preventDefault();
        var keys_no_write = ["CapsLock", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Backspace"];
        for ( var key in keys_no_write){
            if (event.key === key){
                return;
            }
        }
        if (event.altKey || event.ctrlKey){
            return;
        }
        if (event.shiftKey && event.key != 'shift'){
            var value = event.key;
            var cursorPosStart = $(event.target).prop('selectionStart');
            var cursorPosEnd = $(event.target).prop('selectionEnd');
            var v = $(event.target).val();
            var textBefore = v.substring(0, cursorPosStart);
            var textAfter  = v.substring(cursorPosEnd, v.length);
            $(event.target).val(textBefore + value + textAfter);
            event.target.setSelectionRange(cursorPosStart+1, cursorPosStart+1);
        }
    },
    _onKeydownDeliveryNote: function(event){
        event.preventDefault();
        var value = event.key;
        var cursorPosStart = $(event.target).prop('selectionStart');
        var cursorPosEnd = $(event.target).prop('selectionEnd');
        if (event.key === "CapsLock"|| event.altKey || event.ctrlKey || event.shiftKey){
            return;
        }else if (event.key === "ArrowLeft"){
            event.target.setSelectionRange(cursorPosStart-1, cursorPosStart-1);
            return;
        }else if (event.key === "ArrowRight"){
            event.target.setSelectionRange(cursorPosStart+1, cursorPosStart+1);
            return;
        }else if (event.key === "ArrowUp"){
            var chars = this.getCharacterPerLine(event.target);
            event.target.setSelectionRange(cursorPosStart-chars, cursorPosStart-chars);
            return;
        }else if (event.key === "ArrowDown"){
            var chars = this.getCharacterPerLine(event.target);
            event.target.setSelectionRange(cursorPosEnd+chars, cursorPosEnd+chars);
            return;
        }
        var cursorPosBack = cursorPosStart;
        var v = $(event.target).val();
        if( value === 'Backspace' && cursorPosStart == cursorPosEnd){
            value = "";
            cursorPosBack --;
        }else if(value === 'Backspace' && cursorPosStart != cursorPosEnd){
            value = "";
        }
        var textBefore = v.substring(0, cursorPosBack);
        var textAfter  = v.substring(cursorPosEnd, v.length);

        $(event.target).val(textBefore + value + textAfter);
        event.target.setSelectionRange(cursorPosBack+1, cursorPosBack+1);
    },
    getCharacterPerLine: function(target) {
        var w = target.clientWidth + 20;
        var fSize = window.getComputedStyle(target, null).getPropertyValue('font-size');
        fSize = parseFloat(fSize);
        return (w / fSize) * 2;
    },
    show: function(options){
        var self = this;
        this._super(options);
        var order = self.pos.get_order();
        $('#delivery_note').val(order.get_observations() || '');
        $('#delivery_note').keydown(function (ev){self._onKeydownDeliveryNote(ev);});
        $('#delivery_note').keyup(function (ev){self._onKeyupDeliveryNote(ev);});
    },
    click_confirm: function(){
        var self = this;
        var order = self.pos.get_order();
        order.set_observations($('#delivery_note').val() || false);
        self._super();
    },
});
});