import shutil
import os.path
import random
import sys
import time
import asyncio
from ftplib import FTP
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from configparser import ConfigParser
import ftplib
import pidfile

# GLOBAL VARIABLES
#check config.ini for details                                                   
videosPath = ""
movePath = ""
limitNoChangeTime=0
minFilesUpload=0                    
global_percentComplete = '0';
file_deletion = 'True';

# LOAD CONFIG FILE
def Setup():

    global videosPath, movePath, limitNoChangeTime, file_deletion


    config = ConfigParser()
    config.read("config.ini")

    try:
        config_data = config['default']
        print ("Config file loaded. FTP:",config_data['ftp_host'] )
    except Exception as err:
        print (err)
        print(bcolors.FAIL +"Something went wrong while loading config file!"+bcolors.ENDC)
        exit()
    minFilesUpload = int(config_data['minFilesUpload'])    
    file_deletion = config_data['file_deletion']
    videosPath = config_data['files_dir']   
    movePath = config_data['files_move_dir']
    limitNoChangeTime = int(config_data['limitNoChangeTime']) 

         # Ftp login and setup

    try: 
        ftp = ftplib.FTP()

        ftp.connect(config_data['ftp_host'], int(config_data['ftp_port'])) #port has to be int, idk why
        print (bcolors.HEADER, ftp.getwelcome(), bcolors.ENDC)
        try:
            print ("Logging in...")

            ftp.login(config_data['ftp_username'], config_data['ftp_password'])
            ftp.cwd(config_data['ftp_path'])
            print (bcolors.OKGREEN+"Logged-in."+bcolors.ENDC)

        except Exception as err:
            print (err)
            print(bcolors.FAIL +"Credencials Error!"+bcolors.ENDC)
            exit() 
    except Exception as err:
        print (err)
        print(bcolors.FAIL +"Failed to reach the FTP server"+bcolors.ENDC)
        exit()
               
        
    return(ftp)



#PROGRESS PERCENTAGE
class FtpUploadTracker:
    
    sizeWritten = 0
    totalSize = 0
    lastShownPercent = 0
    percentComplete = 0
    def __init__(self, totalSize):
        self.totalSize = totalSize
    
    def handle(self, block):
        global global_percentComplete
        self.sizeWritten += 1024
        percentComplete = round((float(self.sizeWritten) / float(self.totalSize)) * 100)
        global_percentComplete = str(percentComplete)
        if (self.lastShownPercent != percentComplete):
            self.lastShownPercent = percentComplete
           
                                                     
            sys.stdout.write("  " + str(percentComplete) + "% uploaded... \r")
            sys.stdout.flush()


# CHECK IF UPLOAD HAS FREEZED
async def check_freeze():   
  while True:

        old_percentComplete = global_percentComplete
        
        await asyncio.sleep (limitNoChangeTime);

        #print("current:",global_percentComplete,"old:",old_percentComplete)

        if old_percentComplete == global_percentComplete:
            print (bcolors.FAIL + "  Taking too long: ", " - ", old_percentComplete, " = " ,global_percentComplete, bcolors.ENDC);
            os.remove("./ytdlpToFTP.pid")
            os.execv(sys.executable, ['python3'] + sys.argv) #restarts script

            

# FILE OPERATIONS AND UPLOAD    
async def upload_files():

    
    async def upload():
        global ftp, global_percentComplete;
        quanttotal= list_files();

        
        for file in os.listdir(videosPath):
            if file.endswith(".json") or file.endswith(".mkv") or file.endswith(".mp4") or file.endswith(".webm"):       
                try:            

                    file_path = os.path.join(videosPath, file)      
                    fileftp = open(file_path, 'rb')
                    totalSize = os.path.getsize(file_path)               #file size
                    print ("Started uploading:",file,"(",quanttotal,"remaining.)", bcolors.OKCYAN, format_bytes(totalSize), bcolors.ENDC ) #printing file information 
              
              

                    uploadTracker = FtpUploadTracker(int(totalSize))
                    await asyncio.get_event_loop().run_in_executor(None, ftp.storbinary, f'STOR {file}', fileftp, 1024, uploadTracker.handle) 
                    global_percentComplete = '0'

                    quanttotal = quanttotal-1;

                    print (bcolors.OKCYAN,datetime.now().strftime('%H:%M:%S'),"[OK] Finished uploading!" + bcolors.ENDC);

                    
                    if file_deletion == 'True':            
                        os.remove(file_path)  
                    else: 
                        shutil.move( file_path,  movePath)
  
                except Exception as err:
                    print (err)
                    print (bcolors.FAIL + 'An ERROR has occured during the upload!' + bcolors.ENDC)
                    continue     
                            
       
    def list_files():
        quanttotal = 0;
        for file in os.listdir(videosPath):
            if file.endswith(".json") or file.endswith(".mkv") or file.endswith(".mp4") or file.endswith(".webm"):
               quanttotal = quanttotal + 1;
        print(bcolors.OKCYAN + "[INFO]", quanttotal, " files were queued."+ bcolors.ENDC)
        return (quanttotal)

    await upload(); 
    quanttotal_list = list_files();
    if (quanttotal_list > minFilesUpload):
        print(quanttotal_list," new files found!")
        await upload();
    print("Finished uploading queue!")
            
            
async def main():

# CHECKS IF ANOTHER INSTANCE IS ALREADY RUNNING
 try:
    with pidfile.PIDFile("./ytdlpToFTP.pid"): #generated in current directory

     #run upload and freeze checker together   
     batch = asyncio.gather(upload_files(), check_freeze()) 
     result_upload, result_freeze = await batch     
        
 except pidfile.AlreadyRunningError:
    print('Already running.') 
    os._exit(1); 

# COLORED TEXT    
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# CALL TO EXIT PROGRAM
def exit():
    
    os.remove("./ytdlpToFTP.pid")
    os._exit(0);


# CORRECT SIZE FROM BYTES
def format_bytes(size):

    
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : "", 1: " kilo", 2: " mega", 3: " giga", 4: " tera"}
    while size > power:
        size /= power
        n += 1
    output = str(str.format("{0:.2f}", size) + str(power_labels[n])+ "bytes")
    output.replace("'","")
    return (output)



if __name__ == "__main__":
    ftp = Setup();
    asyncio.run(main());

exit()
