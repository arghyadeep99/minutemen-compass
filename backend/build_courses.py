"""
Build courses.json from course information
This creates a structured knowledge base of all courses
"""
import json
from pathlib import Path
from typing import List, Dict, Any


def build_courses() -> Dict[str, Any]:
    """Build course data from course descriptions"""
    
    courses = [
        # Fall 2025 Courses
        {
            "course_code": "CICS 110",
            "course_title": "Foundations of Programming",
            "instructors": ["Kirat Arora", "Meng-Chieh Chiu", "Hasnain Heickal", "Maximillian Kuechen", "Dung Viet Pham", "Cole Reilly"],
            "description": "An introduction to computer programming and problem solving using computers. This course teaches you how real-world problems can be solved computationally using programming constructs and data abstractions of a modern programming language. Concepts and techniques covered include variables, expressions, data types, objects, branching, iteration, functions, classes, and methods. We will also cover how to translate problems into a sequence of instructions, investigate the fundamental operation of a computational system and trace program execution and memory, and learn how to test and debug programs. No previous programming experience required.",
            "prerequisites": "R1 (or a score of 15 or higher on the math placement test Part A), or one of the following courses: MATH 101&102 or MATH 104 or MATH 127 or MATH 128 or MATH 131 or MATH 132",
            "credits": 4,
            "semester": "Fall 2025",
            "gen_ed": "R2"
        },
        {
            "course_code": "CICS 127",
            "course_title": "Introduction to Public Interest Technology",
            "instructors": ["Emily Nutwell"],
            "description": "Today's world is complex and tech driven. How do we use the tools of information technology to solve problems in a socially responsible way, i.e., in a way that both empowers us and promotes the well-being of the communities in which we live? In this course, we describe the socio-technical world and pragmatic strategies for promoting personal and social responsibility. We explore the questions: What is the public interest in a socio-technical world? What strategies can we use to promote social responsibility in the public sector, private sector, and general public? What can each of us do to make the world a better place? This course is for everyone at all levels and with all interests. No programming or prerequisites are required. We focus on building skills to think analytically, broadly, and strategically, as well as to communicate effectively about complex problems with societal impact. Assignments will provide students multiple paths to success.",
            "prerequisites": "None",
            "credits": 4,
            "semester": "Fall 2025",
            "gen_ed": "SI"
        },
        {
            "course_code": "CICS 160",
            "course_title": "Object-Oriented Programming",
            "instructors": ["Cole Reilly", "Ella Tuson"],
            "description": "This course will expose students to programming practices beyond the introductory level, concentrating on Object Oriented Programming techniques and an introduction to Data Structures. Students will also study and analyze the complexity of both the algorithms presented in class and of the algorithms they develop. This course also provides experience with the development and analysis of recursive algorithms and programs. Before taking this course, students are expected to have been exposed to the following concepts through a college-level course or equivalent in some high level computer programming language: input and output operations, conditional statements, loops, arrays, recursion, and functions/methods. The course places an emphasis on the careful design and testing of programs.",
            "prerequisites": "CICS 110 (previously INFO 190S) or COMPSCI 121 with a grade of C or better",
            "credits": 4,
            "semester": "Fall 2025",
            "gen_ed": "R2"
        },
        {
            "course_code": "CICS 208",
            "course_title": "Defending Democracy in a Digital World",
            "instructors": ["Ethan Zuckerman"],
            "description": "This course explores the significance of the public sphere - from pamphlets, newspapers and letters to radio, television, the internet and social media - and its relationship to participatory, democratic society. Moving back and forth between the history of the public sphere and contemporary debates about the tensions between media and democracy, students will learn why democracies prescribe protected roles of the media, how media manipulation plays a role in politics, and how media spaces serve as deliberative spaces. Students will write short reaction papers to the readings, which will be used to shape class discussions, and a longer final paper, focused on applying the theories of the public sphere to regulation of contemporary online spaces.",
            "prerequisites": "None",
            "credits": 3,
            "semester": "Fall 2025",
            "gen_ed": "SB",
            "note": "This course does not count toward CS or INFORM Major requirements. Cross-listed with COMM/SPP 208."
        },
        {
            "course_code": "CICS 210",
            "course_title": "Data Structures",
            "instructors": ["Mordecai Golin", "Marc Liberatore"],
            "description": "An introduction to the design, analysis, and implementation of data structures. This course teaches you how to build, test, debug, document, and evaluate objects that encapsulate data and their associated operations using programming constructs and data abstractions of a modern programming language. Concepts and techniques covered include linear and non-linear structures, recursive structures and algorithms, traversal algorithms, binary search trees, balanced trees, priority queues, union-find, hash tables, bloom filters, and graphs. We will also informally compare and contrast the run time efficiency of algorithms and their performance characteristics including the concept of worst-case running time analysis and the classification of algorithms in terms of constant, logarithmic, linear, log linear, quadratic, and exponential time using Big-O notation.",
            "prerequisites": "CICS 160 (previously INFO 190T) with a grade of C or better",
            "credits": 4,
            "semester": "Fall 2025",
            "gen_ed": "R2"
        },
        {
            "course_code": "CICS 237",
            "course_title": "Introduction to Research in the Discipline",
            "instructors": ["Neena Thota"],
            "description": "The Introduction to Research in the Discipline course is part of the CICS Early Research Scholars Program (ERSP). It provides a group-based, dual-mentored research structure designed to provide a supportive and inclusive first research experience for a large number of early-career Computer Science and Informatics majors.",
            "prerequisites": "None",
            "credits": 2,
            "semester": "Fall 2025"
        },
        {
            "course_code": "CICS 256",
            "course_title": "Make: A Hands-on Introduction to Physical Computing",
            "instructors": ["Md Farhan Tasnim Oshim"],
            "description": "Inspired by the Maker movement, this course provides a hands-on introduction to physical computing: sensing and responding to the physical world using computers. Specific topics include: basic electronics and circuit design, microcontroller programming using Arduinos, sensing and responding to the physical world, rapid prototyping (3D printing and laser cutting etc.), soft circuits and wearable electronics. The course will encourage and empower students to invent, design, and build practical hardware projects that interact with the physical world.",
            "prerequisites": "CICS 210 (or COMPSCI 187) with a grade of C or better and completion of the R1 (Basic Math Skills) Gen. Ed.",
            "credits": 4,
            "semester": "Fall 2025",
            "note": "This course has a required lab section, and counts as one of the CS Lab Science Requirement courses for the BS-CS."
        },
        {
            "course_code": "CICS 291C",
            "course_title": "Seminar - Finding your Strengths and Designing your Career",
            "instructors": ["Casey Maloney"],
            "description": "This course is designed to prepare CICS students for their internship and job searches, improve their professional skills (both technical and soft) and help them approach professional development and/or advanced educational opportunities with confidence.",
            "prerequisites": "None",
            "credits": 1,
            "semester": "Fall 2025"
        },
        {
            "course_code": "CICS 291T",
            "course_title": "Seminar - CICS Transfer Success",
            "instructors": ["Emma Anderson"],
            "description": "This seminar is intended to help you become fully prepared to succeed in CICS at UMass. Students in this seminar will be led by an instructor with a detailed understanding of the transfer student experience, and supported by various staff members in CICS. You will learn about which campus and College resources will be most helpful to you, how to best utilize these resources, and where you can look for other opportunities to connect.",
            "prerequisites": "None",
            "credits": 1,
            "semester": "Fall 2025"
        },
        {
            "course_code": "CICS 298A",
            "course_title": "Practicum - Leadership: Communicating Across Expertise",
            "instructors": ["Emma Anderson"],
            "description": "No matter where you end up in tech, you will need to explain concepts, products and ideas to people with different technical backgrounds. This course is intended to help prepare you for these communication tasks. Through the lens of tutoring, we will work on explaining technical ideas clearly and compassionately to others.",
            "prerequisites": "None",
            "credits": 1,
            "semester": "Fall 2025"
        },
        {
            "course_code": "INFO 150",
            "course_title": "A Mathematical Foundation for Informatics",
            "instructors": ["David Barrington"],
            "description": "Mathematical techniques useful in the study of computing and information processing. The mathematical method of definition and proof. Sets, functions, and relations. Combinatorics, probability and probabilistic reasoning. Graphs and trees as models of data and of computational processes.",
            "prerequisites": "R1 math skills recommended. Not intended for Computer Science majors students interested in a majors-level treatment of this material should see COMPSCI 240 and 250 (or MATH 455).",
            "credits": 3,
            "semester": "Fall 2025"
        },
        {
            "course_code": "INFO 203",
            "course_title": "A Networked World",
            "instructors": ["Mohammadhassan Hajiesmaili"],
            "description": "The course will cover the technical foundations of today's communication networks, particularly the Internet. It will also address key social, policy, economic and legal aspects of these networks, their use (and abuse), and their regulation. This course covers computer science topics, but all material will be presented in a way that is accessible to an educated audience with or without a strong technical background.",
            "prerequisites": "None. Not intended for Computer Science majors students interested in a CS majors-level treatment of this material should see COMPSCI 453.",
            "credits": 3,
            "semester": "Fall 2025"
        },
        {
            "course_code": "INFO 248",
            "course_title": "Introduction to Data Science",
            "instructors": ["Gordon Anderson"],
            "description": "This course is an introduction to the concepts and skills involved with the collection, management, analysis, and presentation of data sets and the data products that result from the work of data scientists. Privacy, algorithmic bias and ethical issues are also discussed. Students will work with data from the financial, epidemiological, educational, and other domains. The course provides examples of real-world data that students work with using various software tools. This course consists of two lecture meetings and one lab meeting per week. Readings will be assigned as preparation for each class meeting. A semester project will be assigned. Students work in pairs to develop their project over the semester. The project provides students with an opportunity to work collaboratively to explore the topics in more depth in a specialized domain. A midterm and final exam will be given. Grades are determined by a combination of scores on lab activities, projects, and exam scores.",
            "prerequisites": "a grade of C or or above in the following courses: CICS 110 (or CICS 160 or COMPSCI 119 or COMPSCI 121) with a grade of C or above and either: PSYCH 240, OIM 240, STATISTC 240, RES-ECON 212, SOCIOL 212, OR STATISTC 315/515, OR COMPSCI 240, with a grade of C or above",
            "credits": 4,
            "semester": "Fall 2025",
            "note": "Open to INFORM majors. Software: all software is freely available."
        },
        {
            "course_code": "INFO 324",
            "course_title": "Introduction to Clinical Health Informatics",
            "instructors": ["Sunghoon Lee"],
            "description": "This course aims to introduce the fundamentals of Clinical Health Informatics to prepare students as forerunners of the future of digital health care systems. More specifically, this course aims to teach students the fundamentals of and tools for quantitative analysis of clinical health data and the practical application of the tools on various health data. The detailed components of the course are as follows. Following an overview of the clinical health informatics industry, the course covers a broad range of introductory topics, including the structure of current health care systems, types of health data, the theory and practical use of quantitative analytic methodologies, and ethics related to healthcare. More specifically, this course will introduce key health informatics technologies and standards, including electronic health records, medical claims data, imaging data, free-text clinical notes, patient-reported outcomes, traditional and machine learning-based analytic algorithms, data visualization, and clinical research and experimental procedures. Note, however, that the course is not designed to introduce new types of machine learning or artificial intelligence algorithms for health-related data.",
            "prerequisites": "INFO 248 (or STATISTIC 315;515 or COMPSCI 240) with a grade of C or better",
            "credits": 4,
            "semester": "Fall 2025",
            "note": "This course is taught in the same classroom with students from COMPSCI 524. However, students enrolled in INFO 324 will be evaluated independently of students from COMPSCI 524. This course fulfills a concentration core requirement for the Health and Life Sciences track, and it can be used to fulfill an elective requirement for the Data Science concentration of the Informatics major. Open to INFORM majors."
        },
        {
            "course_code": "INFO 348",
            "course_title": "Data Analytics with Python",
            "instructors": ["Matthew Rattigan"],
            "description": "The modern world is awash with data, and making sense of it requires specialized skills. This course will expose students to commonly used data analytics techniques. Topics include the acquisition, manipulation, and transformation of structured data, exploratory data analysis, data visualization, and predictive modeling. Students in this course will learn and use the Python programming language and tools for working with data. Analysis will be performed using real data sets.",
            "prerequisites": "INFO 248 and CICS 160 (or INFO 190T or COMPSCI 186 or 187), both with a grade of C or better",
            "credits": 3,
            "semester": "Fall 2025",
            "note": "Does not count as a CS Elective (BA or BS). Satisfies one of the Data Science Concentration requirements and counts as an elective for the Health and Life Sciences Concentration for the Informatics major. Open to INFORM majors."
        },
        {
            "course_code": "INFO 390C",
            "course_title": "Introduction to Computational Biology and Bioinformatics",
            "instructors": ["Anna Green"],
            "description": "This course is designed to provide Informatics students with a broad, practical introduction to the field of computational biology and bioinformatics. The course will discuss at a high level the models and algorithms used to analyze biological sequence data, as well as practical applications and data analysis. Background in biology is not assumed. The primary focus of the course will be analysis of genomic data, including sequence alignment, genome assembly, genome annotation, phylogeny construction, mutation effect prediction, population genetics, RNA-seq data analysis, and genotype-phenotype association studies. Throughout the course, we will emphasize the unique challenges to working with biological data. Through lectures and hands-on programming problem sets, students will develop the necessary skills to tackle computational challenges in biology.",
            "prerequisites": "A grade of C or better in INFO 248 or a grade of C or better in both CICS 210 and COMPSCI 240",
            "credits": 3,
            "semester": "Fall 2025",
            "note": "This course counts as a CS Elective toward the CS Major and as an Elective toward the INFORM Major. Open to juniors and seniors in Computer Science or Informatics."
        },
        {
            "course_code": "INFO 490PI",
            "course_title": "Personal Health Informatics",
            "instructors": ["Ravi Karkar"],
            "description": "This course will cover the design of personal health and wellness technologies. Using the personal health informatics model, we will learn various challenges in designing technologies for personal health data collection (e.g., step count, heart rate, or food intake etc.), integration, self-reflection, and behavior change. Going further, students will understand design issues in sharing personal health data and discuss design guidelines for collaborative data collection, reflection, and care. It is difficult to create health technologies that can successfully be integrated into people's daily life due to many obstacles in individuals' data collection, integration, self-reflection, and sharing practices. Understanding these challenges is an important part of designing Health Technologies. Therefore, this course will cover HCI and design thinking methods that students can leverage to understand the adoption and use of Health Technologies and to design effective Health Technologies. Moreover, visualizations facilitate people to gain insights from their data, so we will cover common visualization approaches used in the personal data contexts. Students will apply the design issues taught during lecture to a team-based semester-long personal health application design project.",
            "prerequisites": "INFO 248 (or COMPSCI 240) and CICS 210 (or COMPSCI 186 or COMPSCI 187) all with a grade of C or better",
            "credits": 4,
            "semester": "Fall 2025",
            "note": "This course satisfies the IE requirement for Informatics majors and it also counts as an elective for all concentrations of the Informatics major."
        },
        
        # Spring 2026 Courses (from web search)
        {
            "course_code": "CICS 110",
            "course_title": "Foundations of Programming",
            "instructors": ["Cole Reilly", "Ella Tuson"],
            "description": "An introduction to computer programming and problem solving using computers. This course teaches you how real-world problems can be solved computationally using programming constructs and data abstractions of a modern programming language. Concepts and techniques covered include variables, expressions, data types, objects, branching, iteration, functions, classes, and methods. We will also cover how to translate problems into a sequence of instructions, investigate the fundamental operation of a computational system and trace program execution and memory, and learn how to test and debug programs. No previous programming experience required.",
            "prerequisites": "R1 (or a score of 15 or higher on the math placement test Part A), or one of the following courses: MATH 101&102 or MATH 104 or MATH 127 or MATH 128 or MATH 131 or MATH 132",
            "credits": 4,
            "semester": "Spring 2026",
            "gen_ed": "R2"
        },
        {
            "course_code": "COMPSCI 240",
            "course_title": "Reasoning Under Uncertainty",
            "instructors": ["Shiting Lan", "Ghazaleh Parvini", "Gayane Vardoyan"],
            "description": "Develops mathematical reasoning skills for problems involving uncertainty, covering topics like counting, probability, probabilistic reasoning, and statistical topics.",
            "prerequisites": "CICS 160 (previously INFO 190T or COMPSCI 187) or CICS 210 and MATH 132, all with a grade of C or better",
            "credits": 4,
            "semester": "Spring 2026"
        },
        {
            "course_code": "COMPSCI 250",
            "course_title": "Introduction to Computation",
            "instructors": ["David Barrington", "Mordecai Golin"],
            "description": "Introduces discrete mathematics concepts useful to computer science, including set theory, formal languages, propositional and predicate calculus, relations and functions, and basic number theory.",
            "prerequisites": "CICS 160 (previously INFO 190T or COMPSCI 187 or E&C-ENG 241, or CICS 210) and MATH 132, all with a grade of C or better",
            "credits": 4,
            "semester": "Spring 2026"
        },
        {
            "course_code": "COMPSCI 325",
            "course_title": "Introduction to Human-Computer Interaction",
            "instructors": ["Ella Tuson"],
            "description": "Focuses on designing for human use, covering design methodologies, evaluation methodologies, human information processing, cognition, and perception.",
            "prerequisites": "COMPSCI 187 (or CICS 210) with a grade of C or better OR INFO 248 and COMPSCI 186 (or 187 or CICS 160; INFO 190T) with a grade of C or better",
            "credits": 3,
            "semester": "Spring 2026"
        },
        {
            "course_code": "COMPSCI 453",
            "course_title": "Computer Networks",
            "instructors": ["Parviz Kermani"],
            "description": "Introduces fundamental concepts in the design and implementation of computer networks, focusing on the Internet's TCP/IP protocol suite.",
            "prerequisites": "COMPSCI 377 and COMPSCI 445, both with a grade of C or better",
            "credits": 3,
            "semester": "Spring 2026"
        },
        {
            "course_code": "COMPSCI 589",
            "course_title": "Machine Learning",
            "instructors": ["Benjamin Marlin"],
            "description": "Introduces core machine learning models and algorithms for classification, regression, clustering, and dimensionality reduction, with an emphasis on model selection, regularization, and empirical evaluation.",
            "prerequisites": "MATH 545 and COMPSCI 240 and STATISTC 315/515, all with a grade of C or better",
            "credits": 3,
            "semester": "Spring 2026"
        },
        {
            "course_code": "INFO 348",
            "course_title": "Data Analytics with Python",
            "instructors": ["Matthew Rattigan"],
            "description": "The modern world is awash with data, and making sense of it requires specialized skills. This course will expose students to commonly used data analytics techniques. Topics include the acquisition, manipulation, and transformation of structured data, exploratory data analysis, data visualization, and predictive modeling. Students in this course will learn and use the Python programming language and tools for working with data. Analysis will be performed using real data sets.",
            "prerequisites": "INFO 248 and CICS 160 (or INFO 190T or COMPSCI 186 or 187), both with a grade of C or better",
            "credits": 3,
            "semester": "Spring 2026",
            "note": "Does not count as a CS Elective (BA or BS). Satisfies one of the Data Science Concentration requirements and counts as an elective for the Health and Life Sciences Concentration for the Informatics major. Open to INFORM majors."
        }
    ]
    
    # Create lookup by course code
    courses_by_code = {}
    for course in courses:
        code = course["course_code"]
        if code not in courses_by_code:
            courses_by_code[code] = []
        courses_by_code[code].append(course)
    
    # Count by semester
    fall_2025_count = sum(1 for c in courses if c["semester"] == "Fall 2025")
    spring_2026_count = sum(1 for c in courses if c["semester"] == "Spring 2026")
    
    return {
        "courses": courses,
        "courses_by_code": courses_by_code,
        "semesters": {
            "fall_2025": fall_2025_count,
            "spring_2026": spring_2026_count
        },
        "total_courses": len(courses),
        "unique_course_codes": len(courses_by_code)
    }


def main():
    """Main function to build and save courses"""
    import sys
    
    # Check if we should use scraper instead of manual data
    use_scraper = "--scrape" in sys.argv or "-s" in sys.argv
    
    if use_scraper:
        # Use the CourseScraper with caching
        from course_scraper import CourseScraper
        
        scraper = CourseScraper()
        courses_data_raw = scraper.scrape_all_courses(use_cache=True)
        
        # Convert to same format as build_courses()
        all_courses = []
        for semester, courses in courses_data_raw.items():
            for course in courses:
                all_courses.append(course)
        
        courses_by_code = {}
        for course in all_courses:
            code = course["course_code"]
            if code not in courses_by_code:
                courses_by_code[code] = []
            courses_by_code[code].append(course)
        
        courses_data = {
            "courses": all_courses,
            "courses_by_code": courses_by_code,
            "semesters": {
                "fall_2025": len(courses_data_raw.get("fall_2025", [])),
                "spring_2026": len(courses_data_raw.get("spring_2026", []))
            },
            "total_courses": len(all_courses),
            "unique_course_codes": len(courses_by_code)
        }
    else:
        # Use manual data (current approach)
        courses_data = build_courses()
    
    # Save to data directory
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "courses.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {courses_data['total_courses']} courses to {output_path}")
    print(f"  - Fall 2025: {courses_data['semesters']['fall_2025']} courses")
    print(f"  - Spring 2026: {courses_data['semesters']['spring_2026']} courses")
    print(f"  - Unique course codes: {courses_data['unique_course_codes']}")
    if use_scraper:
        print(f"  - Data source: Web scraping (with cache)")


if __name__ == "__main__":
    main()

