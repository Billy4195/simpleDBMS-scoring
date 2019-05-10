import os
import re
import zipfile
import json
import subprocess
import tqdm
import argparse

target_folder = 'HW2_submission'
extracted_folder = "extracted"

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

    return IDs

def os_exe_sys_test(work_place, testsuite_path, verbose=False):
    if verbose:
        devnull = None
    else:
        devnull = open(os.devnull, "w")
    rm_test_exe = ["rm", "-rf", os.path.join(work_place, "test")]
    cp_test_exe = ["cp", "-R", testsuite_path, work_place]
    make_clean_exe = ["make", "clean"]
    make_exe = ["make"]
    system_test_exe = ["python", "test/system/system_test.py", "./shell"]
    subprocess.Popen(rm_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(cp_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_clean_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(system_test_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()

def execute_sys_test(result, target_folder, testsuite_path, verbose):
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
        if not os.path.isfile(result_file_path):
            result[ID]["error"] = "system test failed, maybe segmentation fault"
            continue

        with open(result_file_path) as fp:
            stu_result = json.load(fp)

        result[ID].update(stu_result)

        if idx % 5 == 0:
            with open("result.json", "w") as fp:
                json.dump(result, fp)

def cal_score(result_file, score_file, csv_filename):
    # read file
    with open(result_file , 'r') as reader:
        result = json.loads(reader.read())
    with open(score_file , 'r') as reader:
        score = json.loads(reader.read())

    # Get student ID list and testcases list
    # Empty dataframe with student ID
    ID_list = result.keys()
    testsuite_list = list()
    for level in score:
        testsuite_list += score[level]['testsuites']

    final_ = pd.DataFrame(index=ID_list)

    # how many testsuiteuestion in the testcase
    testcase_num = {}
    for stu_id in result:
        if result[stu_id]["error"]:
            continue
        for testsuite in testsuite_list:
            testcase_num[testsuite] = result[stu_id][testsuite]['total']

    # calculate score of each point as dict (score_each_suite_q)
    score_each_suite_q = {}
    for level in score.keys():
        total_questions = 0
        for suite in score[level]['testsuites']:
            total_questions += testcase_num[suite]
        for suite in score[level]['testsuites']:
            score_each_suite_q[suite]= score[level]['score'] / total_questions

    # Calculate score for each student and each testcase, and then sum up each testcase score
    for stu_id in ID_list:
        final_.loc[stu_id,'Id'] = stu_id
        final_.loc[stu_id,'error'] = result[stu_id]['error']
        if result[stu_id]['error']:
            final_.loc[stu_id,'Total_Score'] = 0
            for testsuite in testsuite_list:
                final_.loc[stu_id,testsuite] = 0
        else:
            for testsuite in testsuite_list:
                final_.loc[stu_id,testsuite] = result[stu_id][testsuite]['correct']*score_each_suite_q[testsuite]
            final_.loc[stu_id,'Total_Score'] = final_.loc[stu_id,testsuite_list].sum()

    if csv_filename[-4:] != ".csv":
        csv_filename = csv_filename+'.csv'

    columns = final_.columns.tolist()
    columns.remove("error")
    final_ = final_[ columns + ["error"] ]
    final_.to_csv(csv_filename, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_folder",
                        help="The scoring target folder, may be folder of users' submissions, or single user submission folder")
    parser.add_argument("--extract", help="Give student submission folder which contains zipfiles, the extracted file will be placed into ``target_folder``")
    parser.add_argument("--testsuite_path", default="simpleDBMS/test", help="The testsuites for scoring")
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

    execute_sys_test(result, args.target_folder, args.testsuite_path, args.verbose)
    """
    for idx, ID in enumerate(tqdm.tqdm(IDs)):
        cwd = os.path.join(extracted_folder, ID)
        result[ID] = dict()
        work_place = None
        for root, dirs, files in os.walk(cwd):
            if "Makefile" in files:
                work_place = root
                break

        if not work_place:
            result[ID]["error"] = "No Makefile"
            continue
        else:
            result[ID]["error"] = ""

        #exe_sys_test(work_place)

        result_file_path = os.path.join(work_place, "result.json")
        if not os.path.isfile(result_file_path):
            result[ID]["error"] = "system test failed, maybe segmentation fault"
            continue

        with open(result_file_path) as fp:
            stu_result = json.load(fp)
            
        result[ID].update(stu_result)

        if idx % 5 == 0:
            print("Save record {}".format(idx))
            with open("result.json", "w") as fp:
                json.dump(result, fp)
    """
