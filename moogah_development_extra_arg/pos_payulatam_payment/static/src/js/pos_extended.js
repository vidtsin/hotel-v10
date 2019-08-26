odoo.define('pos_payulatam_payment.pos', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var popups = require('point_of_sale.popups');
    var Model = require('web.DataModel');
    var _t = core._t;

    var _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var journal_model = _.find(this.models, function(model){ return model.model === 'account.journal'; });
            journal_model.fields.push('payulatam','payulatam_config_id');
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });

    models.load_models({
        model: 'payment.acquirer',
        fields: ['name', 'provider', 'environment', 'company_id', 'payulatam_merchantId', 'payulatam_accountId', 'payulatam_apiKey', 'view_template_id'],
        domain: [['provider','=','payulatam']],
        loaded: function(self, pos_payment_acquirer) {
            self.db.pos_payment_acquirer = pos_payment_acquirer;
        },
    });

    screens.PaymentScreenWidget.include({
        click_paymentmethods: function(id) {
            this._super(id);
            // order data
            var currentOrder = this.pos.get_order();
            var plines = currentOrder.get_paymentlines();
            var clients = currentOrder.get_client();
            var payment_acquirer = this.pos.db.pos_payment_acquirer[0];
            // payment method data
            var payulatam_id = payment_acquirer['id']
            var partner_id = currentOrder.get_client() && currentOrder.get_client().id
            var reference = currentOrder['name'];
            var currency_id = this.pos.company.currency_id[0];
            var total = currentOrder.get_total_with_tax();
            // other calculation
            var round_val = (this.pos.currency.rounding).toString();
            var round_size = (round_val.split('.')[1] || []).length;
            var poswer = Math.pow(10, round_size);
            var total_amount = parseInt(total_amount * poswer);
            if (clients){
                for (var i = 0; i < plines.length; i++) {
                    if (plines[i].cashregister.journal['payulatam'] === true){
                        if(currentOrder.get_change() > 0){
                            this.gui.show_popup('error',{
                                'title': _t('Payment Amount Exceeded'),
                                'body': _t('You cannot Pay More than Total Amount'),
                            });
                            return;
                        }
                    }
                }   
            }
            if (!currentOrder.get_client()){
                this.gui.show_popup('error',{
                    'title': _t('Missing Customer'),
                    'body': _t('Please select customer'),
                });
                return;
            }
            if(currentOrder.get_orderlines().length === 0){
                this.gui.show_popup('error',{
                    'title': _t('Empty Order'),
                    'body': _t('There must be at least one product in your order before it can be validated.'),
                });
                return;
            }
            if (clients){
                for (var i = 0; i < plines.length; i++) {
                    if (plines[i].cashregister.journal['payulatam'] === true){
                        new Model('payment.transaction').call('create_transaction_data', [payulatam_id, reference, total, currency_id, partner_id]).fail(function(unused, event) {}).done(function(data) {return data});
                        new Model('payment.acquirer').call('render', [payulatam_id, reference, total, currency_id, partner_id]).fail(function(unused, event) {}).done(function(output) {
                            if(currentOrder.get_change() >= 0){
                                $(document.body).append($(output));
                                $('form .btn-link').click();
                            }
                        });
                    }
                }
            }
            
        },
    });
});
