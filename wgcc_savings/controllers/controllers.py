# -*- coding: utf-8 -*-
from odoo import http

# class WgccSavings(http.Controller):
#     @http.route('/wgcc_savings/wgcc_savings/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wgcc_savings/wgcc_savings/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('wgcc_savings.listing', {
#             'root': '/wgcc_savings/wgcc_savings',
#             'objects': http.request.env['wgcc_savings.wgcc_savings'].search([]),
#         })

#     @http.route('/wgcc_savings/wgcc_savings/objects/<model("wgcc_savings.wgcc_savings"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wgcc_savings.object', {
#             'object': obj
#         })