# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DesignAttachment(models.Model):
    _inherit = ['portal.mixin']
    _name = 'design.image'  # Se mantiene este nombre por compatibilidad con versiones anteriores
    _description = 'Adjunto de Diseño'
    _order = 'sequence, id'

    @api.model_create_multi
    def create(self, vals_list):
        # Generar automáticamente un token de acceso para cada nuevo adjunto
        for vals in vals_list:
            if 'access_token' not in vals:
                record = self.new(vals)
                record._portal_ensure_token()
                vals['access_token'] = record.access_token
        return super().create(vals_list)

    name = fields.Char('Nombre del Archivo', required=True, help='Nombre del archivo adjunto')
    file_data = fields.Binary('Archivo', required=True, attachment=True, help='Contenido del archivo')
    mimetype = fields.Char('Tipo MIME', compute='_compute_mimetype', store=True, help='Tipo MIME del archivo')
    file_size = fields.Integer('Tamaño (bytes)', compute='_compute_file_size', store=True, help='Tamaño del archivo en bytes')
    design_id = fields.Many2one('design.design', string='Diseño', ondelete='cascade', required=True, help='Diseño relacionado')
    sequence = fields.Integer('Secuencia', default=10, help='Orden de visualización')

    @api.depends('file_data')
    def _compute_mimetype(self):
        """Calcula el tipo MIME del archivo basado en su contenido."""
        for record in self:
            if record.file_data:
                record.mimetype = self.env['ir.attachment']._compute_mimetype({'datas': record.file_data})
            else:
                record.mimetype = False

    @api.depends('file_data')
    def _compute_file_size(self):
        """Calcula el tamaño del archivo en bytes."""
        for record in self:
            if record.file_data:
                record.file_size = len(record.file_data)
            else:
                record.file_size = 0
