# this is my tester. feel free to use it.
# python3 ./tester.py all
# python3 ./tester.py q7 te (question) (variation)


import sys
import subprocess
import filecmp
import re
import os
import shutil
import glob

def extract_metrics(vari, text):
    lat = re.search(r"Latency.*?\|\s*(\d+)\s*\|\s*(\d+)\s*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", text, re.DOTALL)
    tot = re.search(r"\|\s*Total\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", text)
    clk = re.search(r"\|\s*ap_clk\s*\|\s*[\d.]+\s*ns\|\s*([\d.]+)\s*ns", text)
    
    latency = lat.group(2) if lat else "NA"
    s_ii = lat.group(4) if lat else "NA"
    bram, dsp, ff, lut = (tot.group(1), tot.group(2), tot.group(3), tot.group(4)) if tot else ("NA", "NA", "NA", "NA")
    
    tp = "NA"
    if clk:
        try:
            c_val = float(s_ii) if s_ii != "NA" else (float(latency) if latency != "NA" else 0)
            if float(clk.group(1)) > 0 and c_val > 0:
                tp = f"{1000.0 / (float(clk.group(1)) * c_val):.3f}"
        except: pass

    return [vari, latency, s_ii, bram, dsp, lut, ff, tp]

def run_question(q, varis=None):
    q_dir = os.path.join("questions", q)
    out_dir = os.path.join("out", q)
    os.makedirs(out_dir, exist_ok=True)

    if not varis:
        varis = sorted(list({re.match(r"fir_(.+?)\.(h|cpp)", os.path.basename(f)).group(1) 
                             for f in glob.glob(os.path.join(q_dir, "fir_*.*")) if re.match(r"fir_(.+?)\.(h|cpp)", os.path.basename(f))}))

    rows = [["Design", "Latency", "Sample II", "BRAM", "DSP", "LUT", "FF", "Throughput (MHz)"]]
    
    for v in varis:
        for ext in ["h", "cpp"]:
            src = os.path.join(q_dir, f"fir_{v}.{ext}")
            if os.path.exists(src): shutil.copy(src, os.path.join("fir128", f"fir.{ext}"))

        subprocess.run(["touch", "fir.cpp"], cwd="fir128")
        test_out = subprocess.run(["make", "test"], cwd="fir128", capture_output=True, text=True)

        if not filecmp.cmp("fir128/out.dat", "fir128/out.gold.dat", shallow=False):
            continue

        hls_out = subprocess.run(["make", "hls"], cwd="fir128", capture_output=True, text=True)
        rpt_out = subprocess.run(["make", "report"], cwd="fir128", capture_output=True, text=True)

        full_log = (test_out.stdout or "") + (test_out.stderr or "") + \
                   (hls_out.stdout or "") + (hls_out.stderr or "") + \
                   (rpt_out.stdout or "") + (rpt_out.stderr or "")

        with open(os.path.join(out_dir, f"{v}.log"), "w") as f:
            f.write(full_log)

        rpt_txt = ""
        rpt_src = "fir128/fir_csynth.rpt"
        rpt_dest = os.path.join(out_dir, f"{v}.rpt")
        
        if os.path.exists(rpt_src):
            shutil.copy(rpt_src, rpt_dest)
            with open(rpt_dest, "r") as f: 
                rpt_txt = f.read()

        rows.append(extract_metrics(v, full_log + "\n" + rpt_txt))

    with open(os.path.join(out_dir, "_table.md"), "w") as f:
        f.write("| " + " | ".join(rows[0]) + " |\n")
        f.write("|" + "|".join(["---"] * len(rows[0])) + "|\n")
        for r in rows[1:]:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")

def main():
    q_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    v_arg = [sys.argv[2]] if len(sys.argv) > 2 else []
    
    targets = [d for d in os.listdir("questions") if os.path.isdir(os.path.join("questions", d))] if q_arg == "all" else [q_arg]
    
    for t in sorted(targets):
        run_question(t, v_arg)

if __name__ == "__main__":
    main()