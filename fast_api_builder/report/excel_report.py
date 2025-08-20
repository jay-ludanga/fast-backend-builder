from datetime import datetime, date
from io import BytesIO
from typing import List, Optional, Tuple, Dict

import xlsxwriter
from fastapi import Request

from fast_api_builder.utils.str_helpers import to_shorter_name


class ExcelReport:
    """
    Create a general class that can be extended to export Excel data.
    """
    columns: List[str] = []
    rows: List[List[Optional[str]]] = []
    worksheet_name: str = 'worksheet'
    title: str = "Report"  # Add a title attribute
    footers: List[Tuple[str, Dict[str, Optional[float]]]] = []

    def __init__(self):
        # Create a workbook and worksheet instance here
        self.workbook = None
        self.worksheet = None

    def header(self, worksheet):
        """
        Add a formatted header and title to the worksheet.
        """
        # Define formats
        title_format = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#D3D3D3',
            'font_size': 14
        })
        wrap_format = self.workbook.add_format({
            'text_wrap': True,
            'bold': True,
            'align': 'center',
            'bg_color': '#D3D3D3'
        })

        # Write the title (centered across columns)
        if self.title:
            num_cols = len(self.columns)
            worksheet.merge_range(0, 0, 0, num_cols - 1, self.title, title_format)

        # Write column headers
        for i, col_name in enumerate(self.columns):
            worksheet.write(1, i, col_name, wrap_format)
            worksheet.set_column(i, i, len(col_name) + 2)  # Adjust column width

    def add_footer(self, worksheet):
        """
        Add footer rows to the worksheet with specified footers.
        """
        footer_format = self.workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'right'
        })

        # Determine the starting row number for the footer
        row_num = len(self.rows) + 2  # Adjust for header and data rows

        # Add each footer entry
        for label, totals in self.footers:
            # Write footer label
            worksheet.write(row_num, 0, label, footer_format)
            for col_name, amount in totals.items():
                col_idx = self.columns.index(col_name)
                if amount is not None:
                    worksheet.write(row_num, col_idx, f"{amount:.2f}", footer_format)
            row_num += 1  # Move to the next row for the next footer item

    def generate_excel(self) -> BytesIO:
        """
        Generate an Excel file with the specified columns and rows.
        """
        output = BytesIO()
        self.workbook = xlsxwriter.Workbook(output)
        self.worksheet = self.workbook.add_worksheet(to_shorter_name(self.worksheet_name))

        # Add header to the worksheet
        self.header(self.worksheet)

        # Write rows
        for row_num, row in enumerate(self.rows, start=2):  # Start from row 2 since row 1 is for headers
            
            if isinstance(row, dict):
                for index, (key, cell) in enumerate(row.items()):
                    if isinstance(cell, datetime):
                        self.worksheet.write(row_num, index, cell.strftime('%Y-%m-%d %H:%M:%S'))
                    elif isinstance(cell, date):
                        self.worksheet.write(row_num, index, cell.strftime('%d-%m-%Y'))
                    elif isinstance(cell, list):
                        self.worksheet.write(row_num, index, ", ".join(map(str, cell)))
                    else:
                        self.worksheet.write(row_num, index, cell)
            elif isinstance(row, list):
                for col_num, cell in enumerate(row):
                    if isinstance(cell, datetime):
                        self.worksheet.write(row_num, col_num, cell.strftime('%Y-%m-%d %H:%M:%S'))
                    elif isinstance(cell, date):
                        self.worksheet.write(row_num, col_num, cell.strftime('%d-%m-%Y'))
                    elif isinstance(cell, list):
                        self.worksheet.write(row_num, col_num, ", ".join(map(str, cell)))
                    else:
                        self.worksheet.write(row_num, col_num, cell)

        # Add footer to the worksheet
        self.add_footer(self.worksheet)

        self.workbook.close()
        output.seek(0)
        return output

