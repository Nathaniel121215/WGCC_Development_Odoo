from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class TrueMoveResCountry(models.Model):
    _inherit = 'res.country'

    is_default_country = fields.Boolean('is Default Country?', default=False)

    @api.constrains('is_default_country')
    def _is_default_country_check(self):
        for rec in self:
            if rec.is_default_country == True:
                if len(self.search([('is_default_country','=',True),('id','!=',rec.id)])):
                    raise ValidationError('There is already a default country!\n - %s'%(self.search([('is_default_country','=',True),('id','!=',rec.id)], limit=1).name))