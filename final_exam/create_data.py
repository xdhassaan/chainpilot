"""
create_data.py — Generates the 5 university PDF knowledge-base documents.
Run once before ingest.py to populate the data/ folder.

Usage:
    python create_data.py
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, spaceAfter=8)
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=6)
bold = ParagraphStyle("bold", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")


def make_doc(filename):
    path = os.path.join(DATA_DIR, filename)
    return SimpleDocTemplate(path, pagesize=letter,
                             topMargin=0.75*inch, bottomMargin=0.75*inch,
                             leftMargin=inch, rightMargin=inch)


def p(text, style=None):
    return Paragraph(text, style or body)


def spacer():
    return Spacer(1, 0.15*inch)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CS Department Catalog
# ─────────────────────────────────────────────────────────────────────────────
def create_cs_catalog():
    doc = make_doc("CS_Department_Catalog.pdf")
    story = []
    story += [p("XYZ National University", h1),
              p("Department of Computer Science", h2),
              p("Undergraduate and Graduate Course Catalog — Spring 2026", body),
              spacer()]

    courses = [
        ("CS101", "Introduction to Programming", "3", "None",
         "Fundamentals of programming using Python. Topics include variables, control flow, "
         "functions, lists, dictionaries, file I/O, and basic algorithm design. "
         "No prior programming experience required."),
        ("CS201", "Data Structures", "3", "CS101",
         "Arrays, linked lists, stacks, queues, trees, heaps, hash tables, and graphs. "
         "Emphasis on time and space complexity analysis (Big-O notation). "
         "Lab sessions require implementation in Python or C++."),
        ("CS301", "Design and Analysis of Algorithms", "3", "CS201, MATH201",
         "Sorting, searching, divide-and-conquer, dynamic programming, greedy algorithms, "
         "graph algorithms (BFS, DFS, Dijkstra, Bellman-Ford, MST). "
         "NP-completeness and computational complexity theory."),
        ("CS302", "Database Systems", "3", "CS201",
         "Relational model, SQL (DDL, DML, DCL), normalization (1NF–BCNF), "
         "transaction management, ACID properties, indexing (B-trees), query optimization. "
         "Lab: PostgreSQL and SQLite projects."),
        ("CS401", "Machine Learning", "3", "CS301, MATH201",
         "Supervised learning (linear regression, logistic regression, SVM, decision trees, "
         "random forests), unsupervised learning (k-means, PCA), model evaluation metrics, "
         "bias-variance tradeoff, cross-validation. Library: scikit-learn."),
        ("CS402", "Computer Networks", "3", "CS302",
         "OSI and TCP/IP models, application layer protocols (HTTP, DNS, SMTP), "
         "transport layer (TCP, UDP), network layer (IP, routing), "
         "link layer (Ethernet, MAC), network security basics."),
        ("CS403", "Software Engineering", "3", "CS302",
         "Software development lifecycle (Agile, Scrum, Waterfall), requirements engineering, "
         "UML diagrams, design patterns (SOLID, GoF patterns), testing strategies, "
         "version control (Git), CI/CD pipelines."),
        ("CS404", "Computer Architecture", "3", "CS201",
         "Von Neumann architecture, instruction set architecture (RISC vs CISC), "
         "assembly language (x86), pipelining, memory hierarchy (cache, RAM, virtual memory), "
         "I/O systems, multiprocessor systems."),
        ("CS501", "Deep Learning", "3", "CS401",
         "Artificial neural networks, backpropagation, CNNs, RNNs, LSTMs, Transformers, "
         "attention mechanisms, transfer learning, regularization (dropout, batch norm). "
         "Frameworks: PyTorch, TensorFlow/Keras."),
        ("CS502", "Natural Language Processing", "3", "CS401",
         "Text preprocessing, word embeddings (Word2Vec, GloVe), sequence models, "
         "BERT and GPT architectures, fine-tuning LLMs, named entity recognition, "
         "sentiment analysis, machine translation, RAG pipelines."),
        ("CS503", "Distributed Systems", "3", "CS402",
         "Distributed computing models, consistency models (CAP theorem, eventual consistency), "
         "consensus algorithms (Raft, Paxos), microservices, message queues (Kafka), "
         "Docker, Kubernetes, cloud deployment patterns."),
        ("CS601", "Research Methods in Computer Science", "3", "Graduate students only",
         "Literature review methodology, research paper writing, experimental design, "
         "statistical analysis, peer review process, IEEE/ACM citation standards. "
         "Culminates in a publishable research proposal. Graduate-level course."),
    ]

    story.append(p("Course Listings", h2))
    for code, name, credits, prereqs, desc in courses:
        story += [
            p(f"{code} — {name}", bold),
            p(f"Credit Hours: {credits} | Prerequisites: {prereqs}"),
            p(desc),
            spacer(),
        ]

    doc.build(story)
    print(f"  Created: CS_Department_Catalog.pdf ({len(courses)} courses)")


# ─────────────────────────────────────────────────────────────────────────────
# 2. EE Department Catalog
# ─────────────────────────────────────────────────────────────────────────────
def create_ee_catalog():
    doc = make_doc("EE_Department_Catalog.pdf")
    story = [p("XYZ National University", h1),
             p("Department of Electrical Engineering", h2),
             p("Undergraduate Course Catalog — Spring 2026", body),
             spacer()]

    courses = [
        ("EE101", "Circuit Analysis I", "4", "None",
         "Kirchhoff's voltage and current laws, Ohm's law, mesh and nodal analysis, "
         "Thevenin and Norton theorems, capacitors, inductors. "
         "Lab: breadboard circuit construction and multimeter measurements."),
        ("EE201", "Circuit Analysis II", "4", "EE101",
         "AC circuit analysis, phasors, impedance, resonance, Laplace transforms, "
         "transfer functions, frequency response (Bode plots), filters. "
         "Lab: oscilloscope and function generator usage."),
        ("EE301", "Signals and Systems", "3", "EE201",
         "Continuous and discrete-time signals, Fourier series and transform, "
         "Laplace and Z-transforms, convolution, sampling theorem (Nyquist), "
         "LTI systems, stability analysis."),
        ("EE302", "Digital Electronics", "3", "EE201",
         "Boolean algebra, logic gates, combinational circuits (mux, decoder, adder), "
         "sequential circuits (flip-flops, registers, counters), "
         "finite state machines, VHDL/Verilog basics."),
        ("EE401", "Microprocessors and Embedded Systems", "3", "EE302",
         "ARM Cortex-M architecture, assembly programming, memory-mapped I/O, "
         "interrupts, timers, UART/SPI/I2C communication protocols, "
         "real-time operating systems (FreeRTOS). Lab: STM32 development board."),
        ("EE402", "Power Systems", "3", "EE301",
         "Three-phase power systems, per-unit analysis, transformers, "
         "synchronous generators and motors, power flow analysis, "
         "protection systems (relays, circuit breakers), smart grid fundamentals."),
        ("EE403", "Communication Systems", "3", "EE301",
         "Analog modulation (AM, FM, PM), digital modulation (ASK, FSK, PSK, QAM), "
         "noise analysis, channel capacity (Shannon theorem), multiplexing (FDM, TDM), "
         "spread spectrum, OFDM, introduction to 5G NR."),
        ("EE501", "Control Systems", "3", "EE302, EE301",
         "Open and closed-loop control, PID controllers, root locus, Bode plots, "
         "Nyquist stability criterion, state-space representation, "
         "controllability, observability, pole placement, introduction to optimal control."),
    ]

    story.append(p("Course Listings", h2))
    for code, name, credits, prereqs, desc in courses:
        story += [
            p(f"{code} — {name}", bold),
            p(f"Credit Hours: {credits} | Prerequisites: {prereqs}"),
            p(desc),
            spacer(),
        ]

    doc.build(story)
    print(f"  Created: EE_Department_Catalog.pdf ({len(courses)} courses)")


# ─────────────────────────────────────────────────────────────────────────────
# 3. BBA Department Catalog
# ─────────────────────────────────────────────────────────────────────────────
def create_bba_catalog():
    doc = make_doc("BBA_Department_Catalog.pdf")
    story = [p("XYZ National University", h1),
             p("Department of Business Administration", h2),
             p("Undergraduate and Graduate Course Catalog — Spring 2026", body),
             spacer()]

    courses = [
        ("BBA101", "Principles of Management", "3", "None",
         "Introduction to management functions: planning, organizing, leading, and controlling. "
         "Organizational structures, decision-making, motivation theories (Maslow, Herzberg), "
         "leadership styles, and communication in organizations."),
        ("BBA201", "Business Finance", "3", "BBA101",
         "Time value of money, NPV and IRR analysis, capital budgeting, "
         "cost of capital (WACC), capital structure theory (Modigliani-Miller), "
         "dividend policy, working capital management, risk and return."),
        ("BBA301", "Marketing Management", "3", "BBA101",
         "Marketing mix (4Ps: product, price, place, promotion), consumer behavior, "
         "market segmentation and targeting, brand management, "
         "digital marketing, marketing research methods, CRM."),
        ("BBA302", "Human Resource Management", "3", "BBA101",
         "Recruitment and selection, job analysis and design, training and development, "
         "performance management, compensation and benefits, "
         "labor relations, diversity and inclusion, HR analytics."),
        ("BBA401", "Strategic Management", "3", "BBA201, BBA301",
         "Strategic analysis (SWOT, PESTEL, Porter's Five Forces), "
         "competitive advantage, corporate-level strategy (diversification, M&A), "
         "business-level strategy (cost leadership, differentiation), "
         "strategy implementation and balanced scorecard."),
        ("BBA402", "Entrepreneurship and Innovation", "3", "BBA201",
         "Entrepreneurial mindset, opportunity recognition, business model canvas, "
         "lean startup methodology, funding sources (VC, angel, bootstrapping), "
         "intellectual property, scaling a startup, social entrepreneurship."),
        ("BBA501", "MBA Research Methods", "3", "Graduate students only",
         "Quantitative and qualitative research design, hypothesis testing, "
         "regression analysis, survey methodology, case study research, "
         "data analysis with SPSS/R, academic writing for business research. Graduate-level."),
    ]

    story.append(p("Course Listings", h2))
    for code, name, credits, prereqs, desc in courses:
        story += [
            p(f"{code} — {name}", bold),
            p(f"Credit Hours: {credits} | Prerequisites: {prereqs}"),
            p(desc),
            spacer(),
        ]

    doc.build(story)
    print(f"  Created: BBA_Department_Catalog.pdf ({len(courses)} courses)")


# ─────────────────────────────────────────────────────────────────────────────
# 4. University Academic Policies
# ─────────────────────────────────────────────────────────────────────────────
def create_policies():
    doc = make_doc("University_Academic_Policies.pdf")
    story = [p("XYZ National University", h1),
             p("Official Academic Policies — Spring 2026", h2),
             spacer()]

    sections = [
        ("Grading Scale",
         "XYZ National University uses the following grading scale:\n\n"
         "A (Excellent): 85–100% = 4.0 GPA points\n"
         "B (Good): 70–84% = 3.0 GPA points\n"
         "C (Satisfactory): 55–69% = 2.0 GPA points\n"
         "D (Marginal Pass): 45–54% = 1.0 GPA points\n"
         "F (Fail): Below 45% = 0.0 GPA points\n\n"
         "A+ and A- are not used. The GPA is calculated as the weighted average "
         "of grade points multiplied by credit hours across all enrolled courses."),
        ("Graduation Requirements",
         "Undergraduate: Minimum cumulative GPA of 2.0 (on a 4.0 scale) is required for graduation. "
         "Students must complete all program requirements and a minimum of 130 credit hours. "
         "A minimum GPA of 2.5 is required in the major field courses.\n\n"
         "Graduate (Master's): Minimum cumulative GPA of 3.0 required. "
         "Students must complete 36 credit hours including a 6-credit thesis or research project."),
        ("Attendance Policy",
         "A minimum attendance of 75% per course is mandatory. "
         "Students falling below 75% attendance will be barred from the final examination. "
         "Attendance is recorded by the course instructor at every class session. "
         "Medical absences require a certificate from the university health center within 3 days."),
        ("Tuition Fees — Spring 2026",
         "Undergraduate students: Rs. 45,000 per semester (fixed, regardless of credit hours taken).\n"
         "Graduate (Master's) students: Rs. 55,000 per semester.\n"
         "PhD students: Rs. 35,000 per semester (subsidized by research grants).\n"
         "Late payment penalty: Rs. 2,000 per week after the deadline (Week 2 of semester).\n"
         "Fee waiver available for students on merit scholarship (top 5% GPA in previous semester)."),
        ("Academic Calendar",
         "Fall Semester: September 1 – January 31 (including examination period).\n"
         "Spring Semester: February 1 – June 30 (including examination period).\n"
         "Summer Session: July 1 – August 31 (condensed, selected courses only).\n"
         "Midterm examinations are held in Week 8. Final examinations in Weeks 17–18."),
        ("Course Withdrawal Policy",
         "Students may withdraw from a course without academic penalty up to Week 8 of the semester. "
         "After Week 8, withdrawal results in a 'W' grade on the transcript (no GPA impact). "
         "After Week 12, no withdrawal is permitted; the student receives the grade earned. "
         "Full tuition is charged regardless of withdrawal date."),
        ("Academic Integrity",
         "Plagiarism, cheating, and unauthorized collaboration are strictly prohibited. "
         "First offense: Zero on the assignment. "
         "Second offense: Fail the course. "
         "Third offense: Expulsion from the university. "
         "All submitted work may be checked using plagiarism detection software (Turnitin)."),
        ("Dean's List and Honors",
         "Dean's List: Students achieving a GPA of 3.7 or above in any semester with a full credit load (15+ credits). "
         "President's Honor Roll: Cumulative GPA of 3.9 or above at graduation. "
         "Summa Cum Laude: GPA 3.9+. Magna Cum Laude: GPA 3.7–3.89. Cum Laude: GPA 3.5–3.69."),
    ]

    for title, content in sections:
        story += [p(title, h2)]
        for line in content.split("\n"):
            if line.strip():
                story.append(p(line))
        story.append(spacer())

    doc.build(story)
    print(f"  Created: University_Academic_Policies.pdf ({len(sections)} sections)")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Faculty Directory
# ─────────────────────────────────────────────────────────────────────────────
def create_faculty():
    doc = make_doc("Faculty_Directory.pdf")
    story = [p("XYZ National University", h1),
             p("Faculty Directory — Spring 2026", h2),
             p("Contact and specialization information for all full-time faculty.", body),
             spacer()]

    faculty = [
        # CS Department
        ("Dr. Ahmed Khan", "Computer Science", "Machine Learning, Deep Learning, AI Systems",
         "PhD (MIT, 2015)", "ahmed.khan@xyz.edu.pk", "Room CS-301, Block A",
         "Office Hours: Mon/Wed 2:00–4:00 PM. Research group: XYZ AI Lab."),
        ("Dr. Sara Ali", "Computer Science", "Computer Networks, Cybersecurity, Cloud Computing",
         "PhD (Cambridge, 2017)", "sara.ali@xyz.edu.pk", "Room CS-302, Block A",
         "Office Hours: Tue/Thu 10:00 AM–12:00 PM. Lead instructor for CS402."),
        ("Prof. Tariq Hassan", "Computer Science", "Algorithms, Competitive Programming, Theory of Computation",
         "MS (IIT Delhi, 2010)", "tariq.hassan@xyz.edu.pk", "Room CS-201, Block A",
         "Office Hours: Mon/Fri 11:00 AM–1:00 PM. Teaches CS301 and CS101."),
        ("Dr. Zara Ahmed", "Computer Science", "Databases, Distributed Systems, Data Engineering",
         "PhD (ETH Zurich, 2019)", "zara.ahmed@xyz.edu.pk", "Room CS-401, Block B",
         "Office Hours: Wed/Fri 3:00–5:00 PM. Teaches CS302, CS503."),
        ("Dr. Bilal Chaudhry", "Computer Science", "Software Engineering, DevOps, Agile Methods",
         "PhD (LUMS, 2016)", "bilal.chaudhry@xyz.edu.pk", "Room CS-205, Block A",
         "Office Hours: Mon/Thu 9:00–11:00 AM. Teaches CS403. Industry experience at Google."),
        # EE Department
        ("Dr. Umar Farooq", "Electrical Engineering", "Power Systems, Renewable Energy, Smart Grid",
         "PhD (University of Toronto, 2014)", "umar.farooq@xyz.edu.pk", "Room EE-201, Block C",
         "Office Hours: Tue/Thu 2:00–4:00 PM. Teaches EE402, EE101."),
        ("Dr. Amna Raza", "Electrical Engineering", "Communication Systems, Signal Processing, 5G",
         "PhD (Georgia Tech, 2018)", "amna.raza@xyz.edu.pk", "Room EE-301, Block C",
         "Office Hours: Mon/Wed 10:00 AM–12:00 PM. Teaches EE403, EE301."),
        # BBA Department
        ("Dr. Nadia Malik", "Business Administration", "Corporate Finance, Investment Analysis, FinTech",
         "PhD (London School of Economics, 2013)", "nadia.malik@xyz.edu.pk", "Room BBA-101, Block D",
         "Office Hours: Mon/Wed 1:00–3:00 PM. Teaches BBA201, BBA401."),
        ("Prof. Bilal Khan", "Business Administration", "Marketing Strategy, Digital Marketing, Consumer Behavior",
         "MBA (Wharton, 2008)", "bilal.khan@xyz.edu.pk", "Room BBA-201, Block D",
         "Office Hours: Tue/Thu 11:00 AM–1:00 PM. Teaches BBA301. Industry: 15 years in brand management."),
    ]

    for name, dept, specialization, qualification, email, office, notes in faculty:
        story += [
            p(name, bold),
            p(f"Department: {dept}"),
            p(f"Specialization: {specialization}"),
            p(f"Qualification: {qualification}"),
            p(f"Email: {email}"),
            p(f"Office: {office}"),
            p(notes),
            spacer(),
        ]

    doc.build(story)
    print(f"  Created: Faculty_Directory.pdf ({len(faculty)} faculty members)")


if __name__ == "__main__":
    print("Creating university knowledge-base PDFs...")
    create_cs_catalog()
    create_ee_catalog()
    create_bba_catalog()
    create_policies()
    create_faculty()
    print(f"\nAll 5 PDFs saved to: {DATA_DIR}")
