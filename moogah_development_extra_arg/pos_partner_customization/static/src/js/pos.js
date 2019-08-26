// pos_partner_customization js
//console.log("custom callleddddddddddddddddddddd")
odoo.define('pos_partner_customization.pos', function(require) {
    "use strict";

    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var popups = require('point_of_sale.popups');
    var Model = require('web.DataModel');
    var QWeb = core.qweb;

    var _t = core._t;


	// Load Models here...
    var _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var partner_model = _.find(this.models, function(model){ return model.model === 'res.partner'; });
            partner_model.fields.push('main_id_category_id', 'main_id_number', 'afip_responsability_type_id');
            //console.log("partner_modellllllllllllllllllllllllllllllllllll",partner_model)
            
            return _super_posmodel.initialize.call(this, session, attributes);
        },
        
    });



    models.load_models({
        model: 'res.partner.id_category',
        fields: ['id','name','code','afip_code'],
        domain: null,
        loaded: function(self, main_identification) {
            //console.log("111111111111loadedddddddddddddddddddddddddddddddddddd",models);
            self.main_identification = main_identification;
            //console.log("***************self.main_identificationnnnnnnnnnnnn", self.main_identification);
        },
    });


    models.load_models({
        model: 'afip.responsability.type',
        fields: ['id','name','code'],
        domain: null,
        loaded: function(self, afip_responsability) {
            //console.log("111111111111loadedddddddddddddddddddddddddddddddddddd",models);
            self.afip_responsability = afip_responsability;
            //console.log("***************self.afip_responsabilitynnnnnnnnnnnn", self.afip_responsability);
        },
    });


	gui.Gui.prototype.screen_classes.filter(function(el) { return el.name == 'clientlist'})[0].widget.include({
		
		
		save_client_details: function(partner) {
		    var self = this;
		    
		    var fields = {};
		    this.$('.client-details-contents .detail').each(function(idx,el){
		        fields[el.name] = el.value || false;
		    });
		    
			fields['main_id_category_id'] = parseInt($("#entered_identification").val());
			fields['afip_responsability_type_id'] = parseInt($("#entered_afip").val());
			fields['main_id_number'] = ($("#entered_main_id_number").val());
			//console.log("fffffffffffffffffffffffffffffffffffffffffiledss",fields, fields['main_id_number'])
		

		    if (!fields.name) {
		        this.gui.show_popup('error',_t('A Customer Name Is Required'));
		        return;
		    }
		    
		    if (this.uploaded_picture) {
		        fields.image = this.uploaded_picture;
		    }

		    fields.id           = partner.id || false;
		    fields.country_id   = fields.country_id || false;

		    new Model('res.partner').call('create_from_ui',[fields]).then(function(partner_id){
		        self.saved_client_details(partner_id);
		    },function(err,event){
		        event.preventDefault();
		        self.gui.show_popup('error',{
		            'title': _t('Error: Could not Save Changes'),
		            'body': _t('Your Internet connection is probably down.'),
		        });
		    });
		},

        
        
    
	});
	
	           

});
