import os
from typing import Optional, Type

from fastapi import Response, HTTPException
from fastapi.responses import StreamingResponse

from tortoise.exceptions import FieldError

from fast_api_builder.common.request.schemas import PaginationParams
from fast_api_builder.common.response.schemas import ApiResponse
from fast_api_builder.common.schemas import ModelType
from fast_api_builder.crud.gql_controller import CreateSchema, GQLBaseCRUD, UpdateSchema, ResponseSchema
from fast_api_builder.report.excel_report import ExcelReport
from fast_api_builder.report.pdf_report import PDFReport


class ReportBaseController(GQLBaseCRUD[Type[ModelType], CreateSchema, UpdateSchema]):
    def __init__(self, model: Type[ModelType], response_schema: Optional[Type[ResponseSchema]] = None):
        self.model = model
        self.output_path = "output"
        super().__init__(model=model, response_schema=response_schema)

    async def export(self, report_name: str, export_type: str, params: PaginationParams,
                     pdf_orientation: str = "portrait"):
        # try:
            # Validate report and export type
            if export_type not in ["pdf", "xlsx"]:
                raise HTTPException(status_code=400, detail="Invalid export type")

            result = await self.get_multiple(params, [])
            if result.status and result.data.item_count > 0:
                model_class = type(result.data.items[0])
                # Make sure to follow field order in Model
                fields_order = [field.__dict__['model_field_name'] for field in model_class._meta.fields_map.values()]
                titles = [field.replace('_', ' ').title() for field in fields_order if field != 'id']
                # Create dictionary
                items = [
                    [getattr(item, field) for field in fields_order if field != 'id']
                    for item in result.data.items
                ]

                # Prepare the output directory
                os.makedirs(self.output_path, exist_ok=True)

                if export_type == "xlsx":
                    return await self.export_as_excel(items, titles, report_name, model_class)
                elif export_type == "pdf":
                    return await self.export_as_pdf(items, titles, report_name, model_class, pdf_orientation)
        # except Exception as e:
        #     print(e)
        #     log_exception(e)
        #     raise HTTPException(status_code=500, detail=f"Failed to Export Data")


    async def export_as_excel(self, data, titles, report_name, model_class):
        export_instance = ExcelReport()
        export_instance.title = model_class.get_report_description()
        export_instance.columns = titles
        export_instance.rows = data
        export_instance.worksheet_name = model_class.get_report_name()
        excel_file = export_instance.generate_excel()

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=report.xlsx"}
        )

    async def export_as_pdf(self, items, titles, report_name, model_class, orientation='portrait'):
        header_data = {}

        if model_class.get_report_description():
            header_data["Description"] = model_class.get_report_description()
        
        # Create PDF
        pdf = PDFReport(title=model_class.get_report_name(), header_data=header_data, orientation=orientation)
        pdf.add_page()
        # pdf.add_text(f"Summary of the Ledger for the period from {request.start_date} to {request.end_date}.")

        pdf.add_table(data=items, column_titles=titles, borders_layout='ALL') # i.e ALL, INTERNAL, MINIMAL, SINGLE_TOP_LINE

        # Prepare the filename and headers
        filename = f"{report_name}.pdf"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }

        # Return the file as a response
        return Response(content=bytes(pdf.output()), media_type="application/pdf", headers=headers)
