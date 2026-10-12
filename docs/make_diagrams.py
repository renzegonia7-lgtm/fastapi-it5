"""Rebuild the ER diagram and department-transfer workflow diagrams."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
NAVY = "#24486A"
NAVY_DARK = "#18344F"
TEAL = "#238A8D"
GOLD = "#D38A3A"
INK = "#213247"
MUTED = "#526579"
BG = "#F5F8FC"
WHITE = "#FFFFFF"
PALE_BLUE = "#EAF1F8"
PALE_TEAL = "#E7F5F3"
PALE_GOLD = "#FFF3E5"
BORDER = "#B5C5D5"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def center_text(draw, xy, text, face, fill):
    x1, y1, x2, y2 = xy
    b = draw.textbbox((0, 0), text, font=face)
    draw.text(((x1 + x2 - (b[2]-b[0]))/2, (y1+y2-(b[3]-b[1]))/2 - b[1]), text, font=face, fill=fill)


def rounded(draw, box, radius=22, fill=WHITE, outline=BORDER, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, points, fill=TEAL, width=7, head=20):
    import math
    draw.line(points, fill=fill, width=width, joint="curve")
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    angle = math.atan2(y1-y0, x1-x0)
    p1 = (x1 + head*math.cos(angle + math.pi*0.82), y1 + head*math.sin(angle + math.pi*0.82))
    p2 = (x1 + head*math.cos(angle - math.pi*0.82), y1 + head*math.sin(angle - math.pi*0.82))
    draw.polygon([(x1,y1), p1, p2], fill=fill)


def entity(draw, x, y, w, h, title, rows, header=NAVY):
    rounded(draw, (x, y, x+w, y+h), radius=24, fill=WHITE, outline=NAVY, width=4)
    draw.rounded_rectangle((x, y, x+w, y+75), radius=22, fill=header)
    draw.rectangle((x, y+48, x+w, y+75), fill=header)
    center_text(draw, (x+8,y+4,x+w-8,y+72), title, font(29, True), WHITE)
    yy = y + 96
    for row in rows:
        is_key = row.startswith("PK") or row.startswith("FK") or row.startswith("UQ")
        draw.text((x+35, yy), row, font=font(22, is_key), fill=INK)
        yy += 38


def make_er():
    im = Image.new("RGB", (1450, 1500), BG)
    d = ImageDraw.Draw(im)
    center_text(d, (50, 25, 1400, 88), "BEGINNER EMPLOYEE API - ENTITY RELATIONSHIP DIAGRAM", font(31, True), NAVY_DARK)
    center_text(d, (60, 92, 1390, 135), "Primary keys, foreign keys, and data integrity constraints", font(20), MUTED)

    entity(d, 100, 165, 1250, 225, "DEPARTMENTS", [
        "PK  id: INTEGER",
        "UQ  name: TEXT (unique, case-insensitive)",
        "     description: TEXT     |     created_at: DATETIME",
    ])
    # Department to employee relationship
    arrow(d, [(725, 392), (725, 485)], TEAL, 7, 20)
    rounded(d, (800, 405, 1315, 465), 14, PALE_TEAL, PALE_TEAL, 1)
    center_text(d, (810,406,1305,464), "1 department : 0..* employees\nFK: employees.department_id", font(17, True), TEAL)

    entity(d, 100, 500, 1250, 330, "EMPLOYEES", [
        "PK  id: INTEGER",
        "     full_name: TEXT     |     position: TEXT",
        "     salary: REAL > 0",
        "FK  department_id -> departments.id",
        "     employment_status: Active / On Leave / Terminated",
        "     hire_date, created_at, updated_at",
    ])
    # Employee-to-transfer relationship
    arrow(d, [(725, 832), (725, 915)], GOLD, 7, 20)
    rounded(d, (800, 840, 1315, 900), 14, PALE_GOLD, PALE_GOLD, 1)
    center_text(d, (810,841,1305,899), "1 employee : 0..* transfer records\nFK: department_transfers.employee_id", font(16, True), GOLD)

    entity(d, 100, 930, 1250, 330, "DEPARTMENT_TRANSFERS", [
        "PK  id: INTEGER",
        "FK  employee_id -> employees.id",
        "FK  old_department_id -> departments.id",
        "FK  new_department_id -> departments.id",
        "     reason: TEXT (5-300 characters)",
        "     transfer_date: DATETIME",
    ], header=TEAL)

    rounded(d, (100, 1280, 1350, 1408), 18, PALE_BLUE, PALE_BLUE, 1)
    center_text(d, (125,1290,1325,1340), "Every transfer references one employee, one previous department, and one new department.", font(18, True), NAVY)
    center_text(d, (125,1342,1325,1395), "PK = Primary Key     FK = Foreign Key     UQ = Unique     Foreign keys are enabled on every SQLite connection.", font(16), NAVY)
    im.save(OUT / "er_diagram.png", quality=95)


def workflow_box(draw, box, number, title, detail, fill=WHITE, outline=NAVY):
    rounded(draw, box, radius=24, fill=fill, outline=outline, width=4)
    x1,y1,x2,y2 = box
    draw.ellipse((x1+22,y1+20,x1+74,y1+72), fill=outline)
    center_text(draw, (x1+22,y1+20,x1+74,y1+72), str(number), font(22, True), WHITE)
    draw.text((x1+95,y1+18), title, font=font(22, True), fill=NAVY_DARK)
    center_text(draw, (x1+95,y1+59,x2-20,y2-12), detail, font(17), MUTED)


def make_workflow():
    im = Image.new("RGB", (1300, 1600), BG)
    d = ImageDraw.Draw(im)
    center_text(d, (40, 22, 1260, 78), "EMPLOYEE DEPARTMENT TRANSFER WORKFLOW", font(29, True), NAVY_DARK)
    center_text(d, (60, 82, 1240, 125), "Both database changes are saved together or rolled back together.", font(18), MUTED)

    x1, x2 = 110, 1190
    y = [150, 335, 520, 705, 890, 1075, 1260]
    h = 135
    steps = [
        (1, "Request", "The client sends an employee ID, destination department ID, and reason.", PALE_BLUE, NAVY),
        (2, "Validate input", "Pydantic checks IDs, field lengths, and the transfer reason.", PALE_BLUE, NAVY),
        (3, "Check records", "The service confirms the employee and destination department exist.", PALE_BLUE, NAVY),
        (4, "Begin transaction", "One SQLite connection is used for the related database writes.", PALE_TEAL, TEAL),
        (5, "Update employee", "Change department_id and update the employee timestamp.", PALE_BLUE, NAVY),
        (6, "Insert transfer history", "Save employee ID, old/new department IDs, reason, and date.", PALE_BLUE, NAVY),
        (7, "Commit transaction", "Commit only after both the employee update and history insert succeed.", PALE_TEAL, TEAL),
    ]
    for (num,title,detail,fill,outline), yy in zip(steps,y):
        workflow_box(d,(x1,yy,x2,yy+h),num,title,detail,fill,outline)
    for i in range(6):
        arrow(d, [(650,y[i]+h+4),(650,y[i+1]-8)], TEAL, 6, 17)

    # Failure path from the database operations to an explicit rollback callout.
    rounded(d, (150, 1430, 1150, 1540), 20, PALE_GOLD, GOLD, 4)
    center_text(d, (175,1440,1125,1483), "If either database write fails", font(21, True), GOLD)
    center_text(d, (175,1482,1125,1528), "SQLite rolls back the transaction, leaving the employee in the original department.", font(17), INK)
    arrow(d, [(1120, 1140),(1230, 1140),(1230, 1483),(1158,1483)], GOLD, 5, 16)
    im.save(OUT / "transfer_workflow.png", quality=95)


if __name__ == "__main__":
    make_er()
    make_workflow()
    print("Wrote er_diagram.png and transfer_workflow.png")
