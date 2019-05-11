import os
import re
import zipfile
import json
import subprocess
import tqdm
import argparse
import pandas as pd

ID_pattern = '^\d{7}'

def mywalk_folder(cwd, ext=None):
    for root, _, files in os.walk(cwd):
        for file_ in files:
            if not ext:
                yield root, file_
            elif ext and file_.endswith(ext):
                yield root, file_

def search_and_extract_zipfile(cwd, extracted_path):
    for root, file_ in mywalk_folder(cwd, ext=".zip"):
        file_path = os.path.join(root, file_)
        with zipfile.ZipFile(file_path) as fp:
            try:
                fp.extractall(extracted_path)
                return True, "Success"
            except:
                return False, "ID extract failed"

    return False, "Can't find any zipfile"

def extract_zipfiles(src_folder, dst_folder):
    if not os.path.isdir(dst_folder):
        os.mkdir(dst_folder)

    IDs = dict()

    sub_folders = os.listdir(src_folder)
    for sub_folder in sub_folders:
        cwd = os.path.join(src_folder, sub_folder)

        # Extract student ID
        ID = re.search(ID_pattern, sub_folder).group(0)
        IDs[ID] = dict()

        # Check destination path
        extracted_path = os.path.join(dst_folder, ID)
        if not os.path.isdir(extracted_path):
            os.mkdir(extracted_path)

        ret, msg = search_and_extract_zipfile(cwd, extracted_path)
        if not ret:
            IDs[ID]["error"] = msg
        else:
            IDs[ID]["error"] = ""

    return IDs

def os_exe_sys_test(work_place, testsuite_path, verbose=False, old_version_test=None):
    if verbose:
        devnull = None
    else:
        devnull = open(os.devnull, "w")
    rm_pre_result_exe = ["rm", "-f", os.path.join(work_place, "result.json")]
    rm_test_exe = ["rm", "-rf", os.path.join(work_place, "test")]
    if old_version_test:
        cp_test_exe = ["cp", "-R", old_version_test, work_place]
    else:
        cp_test_exe = ["cp", "-R", testsuite_path, work_place]
    make_clean_exe = ["make", "clean"]
    make_exe = ["make"]
    system_test_exe = ["python", "test/system/system_test.py", "./shell"]
    subprocess.Popen(rm_pre_result_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(rm_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(cp_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_clean_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(system_test_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()

def execute_sys_test(result, target_folder, testsuite_path, verbose, old_version_test):
    for idx, ID in enumerate(tqdm.tqdm(result)):
        cwd = os.path.join(target_folder, ID)
        result[ID] = dict()
        work_place = None
        for root, file_ in mywalk_folder(cwd):
            if file_ == "Makefile":
                work_place = root
                break

        if work_place is None:
            result[ID]["error"] = "No Makefile"
            continue
        else:
            result[ID]["error"] = ""

        os_exe_sys_test(work_place, testsuite_path, verbose)

        result_file_path = os.path.join(work_place, "result.json")

        #Retry old version test
        if not os.path.isfile(result_file_path):
            print("Retry old version test", ID)
            os_exe_sys_test(work_place, testsuite_path, verbose, old_version_test)

        if not os.path.isfile(result_file_path):
            result[ID]["error"] = "system test failed, maybe segmentation fault"
            continue

        with open(result_file_path) as fp:
            stu_result = json.load(fp)

        result[ID].update(stu_result)

    return result

def cal_question_score(result, testsuite_list, score_dist):
    # how many testsuite in the testcase
    testcase_num = dict()
    for stu_id in result:
        if result[stu_id]["error"]:
            continue
        for testsuite in testsuite_list:
            testcase_num[testsuite] = result[stu_id][testsuite]['total']

    # calculate score of each point as dict (score_each_suite_quest)
    score_each_suite_quest = {}
    for level in score_dist:
        total_questions = 0
        for suite in score_dist[level]['testsuites']:
            total_questions += testcase_num[suite]
        for suite in score_dist[level]['testsuites']:
            score_each_suite_quest[suite]= score_dist[level]['score'] / total_questions

    return score_each_suite_quest

def cal_score(result_file, score_file):
    with open(result_file , 'r') as reader:
        result = json.loads(reader.read())
    with open(score_file , 'r') as reader:
        score_dist = json.loads(reader.read())

    # Get student ID list and testcases list
    ID_list = result.keys()
    testsuite_list = list()
    for level in score_dist:
        testsuite_list += score_dist[level]['testsuites']

    score_table = pd.DataFrame(index=ID_list)

    score_each_suite_quest = cal_question_score(result, testsuite_list, score_dist)

    # Calculate score for each student and each testcase, and then sum up each testcase score
    for stu_id in ID_list:
        score_table.loc[stu_id, 'Student_ID'] = stu_id
        score_table.loc[stu_id, 'error'] = result[stu_id]['error']
        if result[stu_id]['error']:
            score_table.loc[stu_id,'Total_Score'] = 0
            for suite in testsuite_list:
                score_table.loc[stu_id, suite] = 0
        else:
            for suite in testsuite_list:
                score_table.loc[stu_id, suite] = result[stu_id][suite]['correct'] \
                                *score_each_suite_quest[suite]

            score_table.loc[stu_id,'Total_Score'] = score_table.loc[stu_id, testsuite_list].sum()

    return score_table

def store_score_table(score_table, csv_filename):
    if not csv_filename.endswith(".csv"):
        csv_filename = csv_filename + ".csv"

    # Reorder error col to last column
    columns = score_table.columns.tolist()
    columns.remove("error")
    score_table = score_table[ columns + ["error"] ]

    score_table.to_csv(csv_filename, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_folder",
                        help="The scoring target folder, may be folder of users' submissions, or single user submission folder")
    parser.add_argument("--extract", help="Give student submission folder which contains zipfiles, the extracted file will be placed into ``target_folder``")
    parser.add_argument("--testsuite_path", default="simpleDBMS/test", help="The testsuites for scoring")
    parser.add_argument("--old_version_test", default="old_test/test", help="For old version system test")
    parser.add_argument("--result_file", default="hw2_final_score.csv", help="Final result for scoring")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()


    #Extract zip file
    if args.extract:
        IDs = extract_zipfiles(args.extract, args.target_folder)
        result = IDs
    else:
        # May contains student files added manually
        IDs = os.listdir(args.target_folder)
        result = dict()
        for ID in IDs:
            result[ID] = dict()

    result = execute_sys_test(result, args.target_folder,
                     args.testsuite_path, args.verbose,
                     args.old_version_test)

    merged_result_file = "merge_result.json"
    score_distribution_file = "score_distribution.json"
    student_list_file = "student_list.txt"
    sub_score_csv = "hw2_result.csv"

    with open(merged_result_file, "w") as fp:
        json.dump(result, fp)

    score_table = cal_score(merged_result_file, score_distribution_file)
    store_score_table(score_table, sub_score_csv)

    all_stu_IDs = pd.read_csv(student_list_file, header=None, dtype="object")
    scores = pd.read_csv(sub_score_csv, dtype={"Student_ID": "object"})
    all_stu_IDs.columns = ["Student_ID"]
    all_stu_IDs = all_stu_IDs.set_index("Student_ID")
    scores = scores.set_index("Student_ID")

    result = pd.merge(all_stu_IDs, scores, how="left",
                      left_on="Student_ID", right_on="Student_ID",
                      sort=True)

    no_submission = result.isnull().all(axis=1)
    result.loc[no_submission, "error"] = "No submission"
    result.to_csv(args.result_file)

