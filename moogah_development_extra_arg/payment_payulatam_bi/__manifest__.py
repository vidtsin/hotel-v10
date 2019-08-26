# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
{
    'name': 'Website PayuLatam Payment Acquirer',
    'author':'BrowseInfo',
    'category': 'eCommerce',
    'website' : "http://www.browseinfo.in",
    'summary': 'PayuLatam Payment Acquirer integration with Odoo shop',
    'version': '10.0.0.1',
    'description': """PayuLatam Payment Acquirer
		Website PayuLatam Payment Acquirer integration with Odoo shop
		Website Payment Acquirer PayuLatam
		Website Latin america payment gateway with odoo
		Website Latin america payment Acquirer
		Website Payu Payment Acquirer
		Website payment payu Acquirer


		Website Payu Latam Payment Acquirer integration with Odoo shop
		Website Payment Acquirer Payu Latam
		Website Pay u Payment Acquirer
		Website payment pay u Acquirer

		Website Payu-Latam Payment Acquirer integration with Odoo shop
		Website Payment Acquirer Payu-Latam
		Website Pay-u Payment Acquirer
		Website payment pay-u Acquirer


""",
    'depends': ['payment','website_sale'],
    "price": 49,
    "currency": 'EUR',
    'data': [
        'views/res_config_view.xml',
        'views/payulatam.xml',
        'views/payment_acquirer.xml',
        'views/payment_payulatam_template.xml',
        'data/payu.xml',
    ],
    'installable': True,
    "images":["static/description/Banner.png"],
}
