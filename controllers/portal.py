# -*- coding: utf-8 -*-
import logging
import base64
from odoo import http, _

_logger = logging.getLogger(__name__)

from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class DesignPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'design_count' in counters:
            domain = self._get_designs_domain()
            values['design_count'] = request.env['design.design'].search_count(domain)
            _logger.info(f"[PORTAL] Design count calculado: {values['design_count']}")
        return values
    
    def _get_designs_domain(self):
        """Dominio base para buscar diseños visibles para el usuario actual.
        Coincide con la regla de seguridad design_design_rule_cliente."""
        _logger.info("-" * 50)
        _logger.info("[PORTAL] INICIO DE _get_designs_domain")
        
        # Obtener información del usuario y partner
        user = request.env.user
        partner = user.partner_id
        commercial_partner = partner.commercial_partner_id
        
        _logger.info(f"[PORTAL] Usuario: {user.name} (ID: {user.id})")
        _logger.info(f"[PORTAL] Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"[PORTAL] Partner Comercial: {commercial_partner.name} (ID: {commercial_partner.id})")
        _logger.info(f"[PORTAL] Grupos del usuario: {[g.name for g in user.groups_id]}")
        
        # Verificar si el partner tiene algún diseño asociado directamente
        designs_direct = request.env['design.design'].search([('cliente_id', '=', partner.id)])
        _logger.info(f"[PORTAL] Diseños asociados directamente al partner: {len(designs_direct)}")
        for idx, design in enumerate(designs_direct, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Verificar diseños en la jerarquía del partner comercial
        designs_hierarchy = request.env['design.design'].search([('cliente_id', 'child_of', partner.commercial_partner_id.id)])
        _logger.info(f"[PORTAL] Diseños en la jerarquía del partner comercial: {len(designs_hierarchy)}")
        for idx, design in enumerate(designs_hierarchy, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Dominio final con todos los filtros
        _logger.info(f"Partner comercial para el dominio del portal: {partner.commercial_partner_id.name} (ID: {partner.commercial_partner_id.id})")
        domain = [
            '|',
                ('cliente_id', '=', partner.id),
                ('cliente_id', 'child_of', partner.commercial_partner_id.id),
            ('visible_para_cliente', '=', True),
            ('state', 'in', ['cliente', 'correcciones_solicitadas', 'aprobado', 'rechazado', 'esperando_cliente'])
        ]
        
        _logger.info(f"[PORTAL] Dominio de búsqueda: {domain}")
        
        # Verificar cuántos diseños coinciden con el dominio completo
        matching_designs = request.env['design.design'].search(domain)
        _logger.info(f"[PORTAL] Diseños que coinciden con el dominio: {len(matching_designs)}")
        for idx, design in enumerate(matching_designs, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}, Visible: {design.visible_para_cliente}")
        
        return domain
    
    @http.route(['/my/designs', '/my/designs/page/<int:page>'], type='http', auth="user", website=True, sitemap=False)
    def portal_my_designs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        """Muestra la lista de diseños del usuario en el portal."""
        _logger.info("=" * 50)
        _logger.info("[PORTAL] INICIO DE PORTAL_MY_DESIGNS")
        _logger.info(f"[PORTAL] Usuario actual: {request.env.user.name} (ID: {request.env.user.id})")
        _logger.info(f"[PORTAL] Parámetros de URL: page={page}, date_begin={date_begin}, date_end={date_end}")
        _logger.info("=" * 50)
        
        # Obtener el dominio base
        domain = self._get_designs_domain()
        
        # Configurar la paginación
        design_count = request.env['design.design'].search_count(domain)
        pager = portal_pager(
            url="/my/designs",
            total=design_count,
            page=page,
            step=self._items_per_page
        )
        
        # Obtener los diseños paginados
        designs = request.env['design.design'].search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset'],
            order='create_date desc'  # Ordenar por fecha de creación descendente
        )
        
        _logger.info(f"Dominio final usado en la búsqueda: {domain}")
        _logger.info(f"Diseños encontrados para el portal: {[d.name for d in designs]} (Total: {len(designs)})")
        
        # Preparar valores para la plantilla
        values = self._prepare_portal_layout_values()
        values.update({
            'designs': designs,
            'page_name': 'design',
            'default_url': '/my/designs',
            'pager': pager,
            'design_count': design_count,
        })
        
        _logger.info(f"Buscando diseños para el partner {request.env.user.partner_id.id} con el dominio: {domain}")
        _logger.info(f"Se encontraron {design_count} diseños.")
        
        _logger.warning(f"[PORTAL] Mostrando {len(designs)} diseños de un total de {design_count}")
        return request.render("ModuloDisenoOdoo.portal_my_designs", values)
    
    @http.route(['/my/design/<int:design_id>'], type='http', auth="user", website=True, sitemap=False)
    def portal_my_design(self, design_id, access_token=None, **kw):
        """Muestra los detalles de un diseño específico en el portal."""
        try:
            design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Generar tokens de acceso para los adjuntos si no existen
        for attachment in design_sudo.attachment_ids:
            if not attachment.access_token:
                attachment.sudo()._portal_ensure_token()
                
        # Construir datos de archivos usando base64 directamente (sin URLs externas)
        attachments = []
        for attachment in design_sudo.attachment_ids:
            # Obtener los datos del archivo en base64 (usando file_data del modelo design.image)
            file_data = attachment.file_data
            if file_data:
                # Crear data URL para descarga y previsualización
                data_url = f"data:{attachment.mimetype or 'application/octet-stream'};base64,{file_data.decode('utf-8')}"
                
                attachments.append({
                    'id': attachment.id,
                    'name': attachment.name,
                    'mimetype': attachment.mimetype,
                    'file_size': attachment.file_size,
                    'data_url': data_url,
                    'file_extension': attachment.name.split('.')[-1].lower() if '.' in attachment.name else ''
                })

        # Obtener mensajes del chatter - incluir todos los tipos para debug
        messages = []
        for message in design_sudo.message_ids.sorted('create_date', reverse=False):
            # Solo mostrar mensajes que no sean internos y tengan contenido
            if not message.is_internal and message.body:
                messages.append({
                    'id': message.id,
                    'body': message.body,
                    'author_name': message.author_id.name or 'Sistema',
                    'date': message.create_date.strftime('%d/%m/%Y %H:%M'),
                    'message_type': message.message_type,
                    'is_internal': message.is_internal,
                })
        
        # Agregar mensaje de prueba si no hay mensajes
        if not messages:
            messages.append({
                'id': 0,
                'body': '<p>¡Bienvenido al sistema de mensajería! Aquí aparecerán todos los mensajes entre el cliente y el equipo de diseño.</p>',
                'author_name': 'Sistema',
                'date': '15/08/2025 00:40',
                'message_type': 'notification',
                'is_internal': False,
            })

        values = self._prepare_portal_layout_values()
        values.update({
            'design': design_sudo,
            'page_name': 'design',
            'message': kw.get('message'),
            'report_type': 'html',
            'access_token': design_sudo.access_token,
            'attachments': attachments,
            'messages': messages,
        })
        return request.render("ModuloDisenoOdoo.portal_my_design", values)
    
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values['design_count'] = request.env['design.design'].search_count(self._get_designs_domain())
        _logger.warning(f"[PORTAL] Portal layout - design_count: {values['design_count']}")
        return values
    
    @route(['/my/design/approve'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Aprobar el diseño
        if hasattr(design_sudo, 'action_aprobado_por_cliente'):
            design_sudo.sudo().action_aprobado_por_cliente()
        else:
            # Fallback manual si no existe el método
            design_sudo.sudo().write({
                'state': 'aprobado',
                'fecha_aprobacion_cliente': request.env.cr.now(),
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_approved")
    
    @route(['/my/design/approve-with-changes'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_with_changes_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Aprobar con correcciones
        if hasattr(design_sudo, 'action_aprobado_con_correcciones'):
            design_sudo.sudo().action_aprobado_con_correcciones(message)
        else:
            # Fallback manual
            design_sudo.sudo().write({
                'state': 'correcciones_solicitadas',
                'mensaje_cliente': message,
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_approved_with_changes")
    
    @route(['/my/design/reject'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def reject_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Rechazar el diseño
        if hasattr(design_sudo, 'action_rechazado_por_cliente'):
            design_sudo.sudo().action_rechazado_por_cliente(message)
        else:
            # Fallback manual
            design_sudo.sudo().write({
                'state': 'rechazado',
                'mensaje_cliente': message,
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_rejected")
    
    def _document_check_access(self, model_name, document_id, access_token=None):
        """Verificar acceso a un documento de manera segura para usuarios del portal"""
        try:
            # Obtener el registro con el usuario actual
            document = request.env[model_name].browse(document_id)
            
            # Verificar que el documento existe
            if not document.exists():
                _logger.warning(f"Documento {model_name} ID {document_id} no encontrado")
                raise MissingError(_("El documento no existe o fue eliminado"))
                
            # Verificar que el usuario sea el cliente asignado al diseño
            if document.cliente_id.id != request.env.user.partner_id.id:
                _logger.warning(
                    f"Acceso denegado: Usuario {request.env.user.id} intentó acceder "
                    f"al diseño {document_id} que pertenece al cliente {document.cliente_id.id}"
                )
                raise AccessError(_("No tiene permiso para acceder a este diseño"))
                
            # Verificar permisos básicos de lectura
            try:
                document.check_access_rights('read')
                document.check_access_rule('read')
            except AccessError as e:
                _logger.warning(f"Error de permisos en documento {document_id}: {str(e)}")
                raise AccessError(_("No tiene permiso para ver este documento"))
                
            return document
            
        except Exception as e:
            _logger.error(f"Error en _document_check_access: {str(e)}", exc_info=True)
            raise
    
    @route(['/my/design/<int:design_id>/message'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_design_message(self, design_id, access_token=None, **kw):
        try:
            design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        message_body = kw.get('message_body', '').strip()
        if message_body:
            # Publicar mensaje en el chatter nativo de Odoo
            design_sudo.sudo().message_post(
                body=message_body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=request.env.user.partner_id.id
            )
        
        return request.redirect(f'/my/design/{design_id}?access_token={access_token or design_sudo.access_token}')

    @route(['/my/design/<int:design_id>/comment'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_design_comment(self, design_id, access_token=None, **kw):
        try:
            design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        mensaje_cliente = kw.get('mensaje_cliente', '').strip()
        if mensaje_cliente:
            # Actualizar el campo mensaje_cliente
            design_sudo.sudo().write({
                'mensaje_cliente': mensaje_cliente
            })
            
            # Publicar mensaje en el chatter
            design_sudo.sudo().message_post(
                body=f"<p><strong>Comentario del cliente:</strong></p><p>{mensaje_cliente}</p>",
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
        
        return request.redirect(f'/my/design/{design_id}?access_token={access_token or design_sudo.access_token}')