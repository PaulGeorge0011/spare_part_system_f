# backend/api/app/models/__init__.py
from .spare_part import SparePart
from .requisition_log import RequisitionLog
from .inbound_log import InboundLog
from .outbound_log import OutboundLog
from .user import User
from .operation_log import OperationLog
# 机械备件
from .mechanical_spare_part import MechanicalSparePart
from .mechanical_spare_part_image import MechanicalSparePartImage
from .mechanical_requisition_log import MechanicalRequisitionLog
from .mechanical_inbound_log import MechanicalInboundLog
from .mechanical_outbound_log import MechanicalOutboundLog