# -*- coding: utf-8 -*-
{
    'name': "Moogah - Installer for Analytic Tags apps", 
    'version': '10.0.1.1',
    'description': """
        Instala de forma automática todos los módulos que se necesitan para utilizar Etiquetas Analíticas en Compras (Cotizaciones, Ordenes y Facturas),
        Ventas (Cotizaciones, Ordenes y Facturas), suscripciones y Asientos Contables. No incluye el soporte para Bienes de Uso. 
        """,

    'author': ["Moogah"],
    'website': "http://www.moogah.com",
    'category': 'Setup',
    'depends': [
        'analytic_tag_dimension',
        'vitt_analytic_tags',
        'vitt_analytic_tags_account',
        'vitt_analytic_tags_purchase',
        'vitt_analytic_tags_sale_subscription',
        'vitt_analytic_tags_sale'
     ],
}