odoo.define('vitt_val2words.val2text', function(require) {
    "use strict";
    var Model = require('web.Model');
    var Backbone = window.Backbone;
    var exports = {};

    exports.vitt_val2words = Backbone.Model.extend({
        initialize: function() {
            Backbone.Model.prototype.initialize.call(this);
            this.model = new Model('vitt_val2words.config_text');
        },

        vals2text: function(vitt_val2words_id, amount, currency, context){
            var self = this;
            var result = new $.Deferred();
            var num_to_text =this.model.call('num_to_text', [vitt_val2words_id, amount, currency], {context: this.context});
            num_to_text.fail(function(){
                result.reject();
            });
            num_to_text.then(function(text){
                result.resolve(text);
                self.text = text;
            });
            return result;
         },

    });
    return exports;
});