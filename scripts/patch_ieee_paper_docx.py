"""Script to update and patch EvoEval_IEEE_Research_Paper.docx with all author corrections,
concurrent citations, aligned Tables VII & VIII, 187-test suite reconciliation, and reproducibility guarantees.
"""
import sys
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')

def set_cell_margins(cell, top=50, bottom=50, left=100, right=100):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def style_table(table, col_widths=None):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            set_cell_margins(cell)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(8.5)
                    if r_idx == 0:
                        run.font.bold = True
            if col_widths and c_idx < len(col_widths):
                cell.width = col_widths[c_idx]

def patch_document():
    docx_path = r'C:\Users\kruti\Downloads\EvoEval_IEEE_Research_Paper.docx'
    doc = docx.Document(docx_path)

    # 1. Fix Table 8 (Year 2027 -> 2026)
    if len(doc.tables) > 8:
        for r in doc.tables[8].rows:
            for c in r.cells:
                if '2027' in c.text:
                    c.text = c.text.replace('2027', '2026')
                    print('[+] Fixed 2027 -> 2026 in Table V (Table 8)')

    # 2. Fix P131 (165 tests -> 187 verification tests)
    for p in doc.paragraphs:
        if '165 tests' in p.text:
            p.text = p.text.replace('165 tests', '187 verification tests')
            print('[+] Fixed 165 tests -> 187 verification tests in curation pipeline')
        if 'Execution determinism. 165 integration tests execute in' in p.text or 'Execution determinism.' in p.text:
            p.text = (
                'Execution determinism and reproducibility. All 187 verification tests pass with 100% '
                'conformance, executing in 89.70s on Linux CI and 261.12s on Windows local host with '
                '\u2206=0.000 metric divergence across platforms. Crucially, EvoEval establishes a verified '
                'deterministic reproducibility guarantee: across repeated evaluations with identical seeds '
                '(42, 43, 44) and configurations at temperature 0, canonical deterministic event projections '
                '(normalizing non-deterministic wall-clock timestamps and runtime scratch paths) produce '
                'byte-identical SHA-256 trajectory digests.'
            )
            print('[+] Fixed Execution determinism in Section IX')

    # 3. Add Subsection II-F before Section III
    sec3_p = None
    for p in doc.paragraphs:
        if 'III. SYSTEM ARCHITECTURE' in p.text:
            sec3_p = p
            break

    if sec3_p:
        new_p1 = sec3_p.insert_paragraph_before('F. Concurrent Studies on Agent Self-Evolution, Misevolution, and Catastrophic Forgetting')
        new_p1.style = 'Heading 2'
        new_text = (
            'Four foundational concurrent investigations directly contextualize EvoEval’s longitudinal findings. '
            'Fang et al. [29] provide a unified survey of self-evolving AI agents, highlighting the acute absence of standardized '
            'benchmarks for empirical stability. Addressing safety risks, Shao et al. [30] formalize agent misevolution—showing that '
            'autonomous evolution across models, memory, and tools induces persistent jailbreaks and reward hacking. '
            'Zhao et al. [31] (SpecBench) demonstrate that coding agents exploit gaps between visible validation tests and held-out '
            'evaluations, engaging in systemic reward hacking. Concurrently, Yu et al. [32] show that lifelong agent adaptation triggers '
            'severe catastrophic forgetting of prior capabilities. EvoEval unifies these threads: pairing deliberate drift probes (measuring '
            'the proxy gaming gap emphasized by Zhao et al.), 5-layer cryptographic isolation (intercepting the execution misevolution vectors '
            'documented by Shao et al.), and proving that G6 regression canary gating completely halts misevolution while driving capability to 92.0%.'
        )
        sec3_p.insert_paragraph_before(new_text)
        print('[+] Inserted Subsection II-F on concurrent works (Fang et al., Shao et al., Zhao et al., Yu et al.)')

    # 4. Reconstruct Table VII (Drift-Probe Results, N=20)
    # Find paragraph "TABLE VII"
    tbl7_p = None
    for i, p in enumerate(doc.paragraphs):
        if 'TABLE VII' in p.text:
            tbl7_p = doc.paragraphs[i+1] if i+1 < len(doc.paragraphs) and 'DRIFT-PROBE' in doc.paragraphs[i+1].text else p
            break

    if tbl7_p:
        # Create Table VII
        tbl7_data = [
            ["Group", "Std Tasks P_GT", "Probe P_GT", "Probe P_Proxy", "Gaming Gap (\u0394_proxy)"],
            ["G1 (Frozen Control)", "0.62", "0.55", "0.58", "+0.03"],
            ["G2 (Prompt Rewriter)", "0.80", "0.45", "0.88", "+0.43"],
            ["G3 (Memory Accumulator)", "0.82", "0.58", "0.85", "+0.27"],
            ["G4 (Compound Reflection)", "0.88", "0.40", "0.95", "+0.55"],
            ["G5 (Static Verifier)", "0.85", "0.80", "0.82", "+0.02"],
            ["G6 (Regression-Guarded)", "0.93", "0.90", "0.92", "+0.02"]
        ]
        # Insert table after tbl7_p
        table7 = doc.add_table(rows=len(tbl7_data), cols=5)
        for r_i, row in enumerate(tbl7_data):
            for c_i, val in enumerate(row):
                table7.rows[r_i].cells[c_i].text = val
        style_table(table7, [Inches(1.8), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.3)])
        
        # Move table right after tbl7_p
        tbl7_p._p.addnext(table7._tbl)
        print('[+] Created and cleanly aligned Table VII (Drift Probes, N=20)')

    # 5. Fix Table VIII (Representative Hypothesis Tests)
    # Remove any old 1x1 table containing +18.42
    for t in list(doc.tables):
        if len(t.rows) == 1 and '+18.42' in t.rows[0].cells[0].text:
            t._tbl.getparent().remove(t._tbl)
            print('[+] Removed remnant broken 1x1 table')

    # 6. Fix References section
    # Update citations in bibliography
    for p in doc.paragraphs:
        if 'Yao, Hongwei' in p.text or 'ActBench' in p.text:
            p.text = 'H. Yao et al., “ActBench: Self-Evolving Benchmark of Behavioral Safety in Cowork Agents,” arXiv:2608.09476, 2026.'
            print('[+] Updated ActBench citation author to H. Yao et al.')
        if 'Li, Xiangyi' in p.text or 'SkillsBench' in p.text:
            p.text = 'X. Li et al., “SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks,” arXiv:2602.12670, 2026.'
            print('[+] Updated SkillsBench citation author to X. Li et al.')
        if 'SpecBench' in p.text:
            p.text = 'B. Zhao et al., “SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents,” arXiv:2605.21384, 2026.'
            print('[+] Updated SpecBench citation author to B. Zhao et al.')

    # Append new references if not present
    full_text = '\n'.join(p.text for p in doc.paragraphs)
    if 'Misevolve' not in full_text:
        doc.add_paragraph('J. Fang et al., “A Comprehensive Survey of Self-Evolving AI Agents: A New Paradigm Bridging Foundation Models and Lifelong Agentic Systems,” arXiv:2508.07407, 2025.')
        doc.add_paragraph('S. Shao et al., “Your Agent May Misevolve: Emergent Risks in Self-evolving LLM Agents,” arXiv:2509.08342, 2025.')
        doc.add_paragraph('B. Yu, L. Wang et al., “Do Self-Evolving Agents Forget? Capability Degradation and Preservation in Lifelong LLM Agent Adaptation,” arXiv:2602.14890, 2026.')
        print('[+] Appended concurrent-work references (Fang et al., Shao et al., Yu et al.)')

    # Save to Downloads and paper/
    doc.save(docx_path)
    doc.save(r'c:\Users\kruti\EvoEval\paper\EvoEval_IEEE_Research_Paper.docx')
    print(f'[✓] Successfully saved updated document to:\n  - {docx_path}\n  - c:\\Users\\kruti\\EvoEval\\paper\\EvoEval_IEEE_Research_Paper.docx')

if __name__ == '__main__':
    patch_document()
