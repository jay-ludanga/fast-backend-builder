# from typing import List, Optional
# from fastapi import APIRouter, File, Form, UploadFile, Depends
# from fastapi.params import Query

# from fast_api_builder.common.response.codes import ResponseCode
# from fast_api_builder.common.response.schemas import ApiResponse
# from src.modules.auth.permission_middleware import get_current_user, authorize
# from src.modules.cash.schema import AttachmentCreate


# def build_attach_endpoints(router: APIRouter, path: str, controller, parent_id_name: str,
#                                model_verbose: Optional[str] = None,
#                                security_dependency=Depends(get_current_user)):
#     @router.post(f"{path}/attachments/single/upload")
#     @authorize([f"src.add_{model_verbose}"])
#     def upload_single_attachment(parent_id: int, file: UploadFile = File(...), title: str = Form(...),
#                            current_user: dict = security_dependency):
#         try:
#             attachments: List[AttachmentCreate] = [
#                 AttachmentCreate(
#                     parent_id=parent_id,
#                     title=title,
#                     content=file
#                 )
#             ]
            
#             return controller.upload_attachments(attachments, parent_id_name)
#         except Exception as e:
#             return ApiResponse(
#                 status=False,
#                 code=ResponseCode.FAILURE,
#                 message=f"An error occured while uploading attachment. Retry",
#             )
            
#     @router.post(f"{path}/attachments/upload")
#     @authorize([f"src.add_{model_verbose}"])
#     def upload_attachments(parent_id: int, files: List[UploadFile] = File(...), titles: List[str] = Form(...),
#                            current_user: dict = security_dependency):
#         try:
#             attachments: List[AttachmentCreate] = []
#             for index, file in enumerate(files):
#                 attachments.append(
#                     AttachmentCreate(
#                         parent_id=parent_id,
#                         title=titles[index],
#                         content=file
#                     )
#                 )
#             return controller.upload_attachments(attachments, parent_id_name)
#         except IndexError as e:
#             return ApiResponse(
#                 status=False,
#                 code=ResponseCode.BAD_REQUEST,
#                 message=f"Titles and Files do not match {len(files)} - {len(titles)}",
#             )

#     @router.get(f"{path}/attachments/get")
#     @authorize([f"src.view_{model_verbose}"])
#     def get_attachments(parent_id: int, current_user: dict = security_dependency):
#         return controller.get_attachments(parent_id, parent_id_name)

#     @router.get(f"{path}/attachments/download")
#     @authorize([f"src.change_{model_verbose}"])
#     def download_attachment(attachment_id: int, current_user: dict = security_dependency):
#         return controller.download_attachment(attachment_id)

#     @router.delete(f"{path}/attachments/remove")
#     @authorize([f"src.delete_{model_verbose}"])
#     def delete_attachment(attachment_id: int, current_user: dict = security_dependency):
#         return controller.remove_attachment(attachment_id)

#     return router
