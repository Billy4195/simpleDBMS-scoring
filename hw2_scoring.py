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

def extract_zipfiles():
    if not os.path.isdir(extracted_folder):
        os.mkdir(extracted_folder)

    IDs = list()
    failed_list = list()

    subm_folders = os.listdir(target_folder)
    for stu_folder in subm_folders:
        cwd = os.path.join(target_folder, stu_folder)
        ID = re.search(ID_pattern, stu_folder).group(0)


        extracted_path = os.path.join(extracted_folder, ID)
        if not os.path.isdir(extracted_path):
            os.mkdir(extracted_path)

        found_zip = False
        for root, dirs, files in os.walk(cwd):
            for f in files:
                if f.endswith(".zip"):
                    found_zip = True

                    file_path = os.path.join(root, f)
                    with zipfile.ZipFile(file_path) as fp:
                        try:
                            fp.extractall(extracted_path)
                        except:
                            failed_list.append(ID)
                            print("ID extract failed")

                    break

            if found_zip:
                break


        IDs.append(ID)

    return IDs, failed_list

def exe_sys_test(work_place):
    devnull = open(os.devnull, "w")
    rm_test_exe = ["rm", "-rf", os.path.join(work_place, "test")]
    cp_test_exe = ["cp", "-R", "simpleDBMS/test", work_place]
    make_clean_exe = ["make", "clean"]
    make_exe = ["make"]
    system_test_exe = ["python", "test/system/system_test.py", "./shell"]
    subprocess.Popen(rm_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(cp_test_exe, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_clean_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(make_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()
    subprocess.Popen(system_test_exe, cwd=work_place, stdout=devnull, stderr=devnull).wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_folder",
                        help="The scoring target folder, may be folder of users' submissions, or single user submission folder")
    parser.add_argument("--extract", help="Give student submission folder which contains zipfiles, the extracted file will be placed into ``target_folder``")
    args = parser.parse_args()

    """
    #Extract zip file
    #IDs, failed_list = extract_zipfiles()

    result = {}
    # May contains student files added manually
    IDs = os.listdir(extracted_folder)

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
