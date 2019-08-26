odoo.define('pos_id_number_customization.pos', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var DB = require('point_of_sale.DB');
    var core = require('web.core');
    var utils = require('web.utils');

    var _t = core._t;

    models.load_fields('res.partner', 'main_id_number');

    DB.include({
        _partner_search_string: function (partner) {
            var str = partner.name;
            if (partner.barcode) {
                str += '|' + partner.barcode;
            }
            if (partner.address) {
                str += '|' + partner.address;
            }
            if (partner.phone) {
                str += '|' + partner.phone.split(' ').join('');
            }
            if (partner.mobile) {
                str += '|' + partner.mobile.split(' ').join('');
            }
            if (partner.email) {
                str += '|' + partner.email;
            }
            if (partner.main_id_number) {
                str += '|' + partner.main_id_number;
            }
            str = '' + partner.id + ':' + str.replace(':', '') + '\n';
            return str;
        },
    });


});
