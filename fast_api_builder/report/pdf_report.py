from datetime import datetime
from typing import Dict, List, Any

from fpdf import FPDF
from fpdf.table import Table


class PDFReport(FPDF):
    def __init__(self, title: str, header_data: Dict[str, str], orientation: str = 'portrait', project: str = None):
        self.title = title
        self.header_data = header_data
        self.project = project
        super().__init__(orientation)

    @staticmethod
    def stringfy_value(value) -> str:
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d")
        elif isinstance(value, float):
            value = f"{value:.2f}"  # Format float with two decimal places
        elif isinstance(value, int):
            value = str(value)  # Convert int to string

        elif isinstance(value, list):
            value = str(value[0]) if value else ""
        else:
            value = str(value)  # Convert other types to string

        return value

    def header(self, size=9):
        self.set_font("Arial", "B", size)
        self.cell(0, 10, "THE UNITED REPUBLIC OF TANZANIA", border=False, ln=True, align="C")
        # self.set_image_filter("DCTDecode")
        # Add vertical space after the text (e.g., 10 units)

        # Image settings
        logo_width = 22  # Width of the image
        page_width = self.epw  # Effective page width
        x_position = (page_width - logo_width) / 2  # Centered x position

        # Add the centered image (move it down by adjusting y)
        self.image('assets/images/logo-light.png', x=x_position + 5, y=17, w=logo_width, alt_text="Logo")
        self.ln(20)
        self.cell(0, 5, "PRESIDENT'S OFFICE PLANNING AND INVESTMENT", border=False, ln=True, align="C")
        if self.project:
            self.cell(0, 5, self.project, border=False, ln=True, align="C")
        self.cell(0, 10, self.title, border=False, ln=True, align="C")
        self.set_font("Arial", "", size)
        for key, value in self.header_data.items():
            self.cell(0, 10, f"{key}: {value}", border=False, ln=True, align="L")
        self.ln(5)

    def footer(self):
        self.set_y(-15)

        # Draw a line above the footer
        self.set_draw_color(0, 0, 0)  # Set line color to black
        self.line(10, self.get_y(), 200, self.get_y())

        self.set_font("Arial", "I", 8)

        # Current date
        current_datetime = datetime.now().strftime("%B %d, 2024, %I:%M %p")

        self.cell(0, 5, "muarms: (National Investment Database System)", 0, 1, "L")

        # Printed date on the left
        self.cell(0, 5, f"Printed {current_datetime}", 0, 0, "L")  # Move to next line with ln=1

        # Add "PFMS: (Project Finance Management System)" below the printed date

        # Page number on the right (adjust vertical position for clarity)
        self.set_y(-15)  # Reset the y position for the page number to avoid overlap
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "R")

    def add_table(self, data: List[Dict[str, Any]], column_titles: List[str],
                  has_footer: bool = False, footer_labels: List[str] = None,
                  footer_data: List[str | float | int] = None, footer_span: List[int] = None,
                  borders_layout="SINGLE_TOP_LINE"):
        self.set_font(size=7)
        with self.table(text_align="CENTER", num_heading_rows=1, borders_layout=borders_layout) as table:
            # Add column titles
            row = table.row()
            for title in column_titles:
                row.cell(title)

            # Add table data
            for data_row in data:
                row = table.row()

                for value in data_row:
                    row.cell(self.stringfy_value(value))

            # Optionally add table footer
            if has_footer:
                self.add_table_footer(table, footer_labels=footer_labels, footer_data=footer_data,
                                      footer_span=footer_span)

    def add_table_footer(self, table: Table, footer_labels: List[str] = None,
                         footer_data: List[str] = None, footer_span: List[int] = None):
        """Default implementation for the table footer with dynamic labels."""
        if footer_labels and footer_data and footer_span:
            row = table.row()
            for label, span in zip(footer_labels, footer_span):
                row.cell(label, colspan=span)
            for footer_value in footer_data:
                row.cell(self.stringfy_value(footer_value))

    def add_text(self, text: str, size=9):
        self.set_font("Arial", "", size)
        self.multi_cell(0, 10, text)
