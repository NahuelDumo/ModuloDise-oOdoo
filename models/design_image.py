# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DesignAttachment(models.Model):
    _inherit = ['portal.mixin']
    _name = 'design.image' # Mantenemos el nombre por retrocompatibilidad
    _description = 'Adjunto de Diseño'
    _order = 'sequence, id'

    @api.model_create_multi
    def create(self, vals_list):
        # Asegurarse de que cada nuevo adjunto tenga un token de acceso
        for vals in vals_list:
            if 'access_token' not in vals:
                record = self.new(vals)
                record._portal_ensure_token()
                vals['access_token'] = record.access_token
        return super().create(vals_list)

    name = fields.Char('Nombre de archivo', required=True)
    file_data = fields.Binary('Adjunto', required=True, attachment=True)
    mimetype = fields.Char('Tipo de archivo', compute='_compute_mimetype', store=True)
    file_size = fields.Integer('Tamaño (bytes)', compute='_compute_file_size', store=True)
    design_id = fields.Many2one('design.design', string='Diseño', ondelete='cascade', required=True)
    sequence = fields.Integer('Secuencia', default=10)

    @api.depends('file_data')
    def _compute_mimetype(self):
        for record in self:
            if record.file_data:
                record.mimetype = self.env['ir.attachment']._compute_mimetype({'datas': record.file_data})
            else:
                record.mimetype = False

    @api.depends('file_data')
    def _compute_file_size(self):
        for record in self:
            if record.file_data:
                record.file_size = len(record.file_data)
            else:
                record.file_size = 0
