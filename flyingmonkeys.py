#!/usr/bin/env python

import os.path
from Tkinter import *
import tkMessageBox

from abc import ABCMeta, abstractmethod
from subprocess import call

class ApplicationInstallModule:
    __metaclass_ = ABCMeta
    
    def __init__(self, installByDefault = False, configureCallback = None, prereqs = None):
        self.prereqs = prereqs
        self.installVar = BooleanVar()
        self.installVar.set(self.IsInstalled() or installByDefault)
        self.configure = configureCallback
    @abstractmethod
    def IsInstalled(self):
        pass
    @abstractmethod
    def Install(self):
        pass
    def SystemCommand(self, args):
        return call(args)
    def Run(self):
        if self.installVar.get() and not self.IsInstalled():
            if self.prereqs is not None:
                for prereq in self.prereqs:
                    prereq.Run()
                
            self.Install()
            if self.configure is not None:
                self.configure(self)

class DownloadInstallerModule(ApplicationInstallModule):
    def __init__(self, url, installationPath, installByDefault = True, configureCallback = None, prereqs = None):
        self.url = url
        self.fileName = url.split("/")[-1]
        self.installationPath = installationPath
        ApplicationInstallModule.__init__(self, installByDefault, configureCallback, prereqs)
    def IsInstalled(self):
        isInstalled = os.path.exists(self.installationPath)
        
        if isInstalled:
            print "Already installed at: " + self.installationPath
        
        return isInstalled
    def Install(self):
        self.SystemCommand(["wget", self.url])
        self.SystemCommand(["chmod", "u+x", self.fileName])
        self.SystemCommand(["sudo", "./" + self.fileName])
        self.SystemCommand(["rm", self.fileName])
        

class BinaryInstallModule(ApplicationInstallModule):
    def __init__(self, downloadUrl, installByDefault = False, stripExtension = True, prereqs = None):
        self.downloadUrl = downloadUrl
        downloadUrlsplit = downloadUrl.split("/")
        self.fileName = downloadUrlsplit[len(downloadUrlsplit) - 1]
        self.stripExtension = stripExtension
        ApplicationInstallModule.__init__(self, installByDefault, prereqs = prereqs)
    def Name(self):
        if self.stripExtension:
            return self.fileName.split(".")[0]
            
        return self.fileName
    def IsInstalled(self):
        isInstalled = os.path.exists("/usr/local/bin/" + self.Name())
        
        if isInstalled:
            print "Already installed at: /usr/local/bin/" + self.Name()
        
        return isInstalled
    def Install(self):
        self.SystemCommand(["wget", self.downloadUrl])
        self.SystemCommand(["chmod", "u+x", self.fileName])
        self.SystemCommand(["sudo", "mv", self.fileName, "/usr/local/bin/" + self.Name()])

class SourceInstallModule(ApplicationInstallModule):
    def __init__(self, downloadUrl, compiledFilePath, unpackedDirectory, prereqs = None):
        self.downloadUrl = downloadUrl
        downloadUrlSplit = downloadUrl.split("/")
        self.compiledFilePath = compiledFilePath
        self.fileName = downloadUrlSplit[len(downloadUrlSplit) - 1]
        self.directory = unpackedDirectory
        ApplicationInstallModule.__init__(self, True, prereqs = prereqs)
    def IsInstalled(self):
        isInstalled = os.path.exists(self.compiledFilePath)
        
        if isInstalled:
            print "Already installed at: " + self.compiledFilePath
        
        return isInstalled
    def Unpack(self):
        if ".zip" in self.fileName:
            self.SystemCommand(["unzip", self.fileName])
            return
            
        if ".tar.gz" in self.fileName or ".tgz" in self.fileName:
            self.SystemCommand(["tar", "xvfz", self.fileName])
            return
        
        Exception("File type not supported.")
    @abstractmethod
    def Configure(self):
        pass
    @abstractmethod
    def Compile(self):
        pass
    @abstractmethod
    def InstallBinaries(self):
        pass
    def Install(self):
        self.SystemCommand(["wget", self.downloadUrl])
        self.Unpack()
        self.Configure()
        self.Compile()
        self.InstallBinaries()
        self.SystemCommand(["rm", self.fileName])
        
class PhpSourceInstallModule(SourceInstallModule):
    def __init__(self, downloadUrl, compiledFilePath, unpackedDirectory, configureOptions = None, prereqs = None):
        self.configureOptions = configureOptions
        SourceInstallModule.__init__(self, downloadUrl, compiledFilePath, unpackedDirectory, prereqs)
    def Configure(self):
        os.chdir(self.directory)
        self.SystemCommand(["phpize"])
        cmd = ["./configure"]
        if self.configureOptions is not None:
            for key in self.configureOptions.keys():
                option = "--" + key
                if len(self.configureOptions[key]) > 0:
                    option += "-" + self.configureOptions[key]
                cmd.append(option)
        self.SystemCommand(cmd)
    def Compile(self):
        self.SystemCommand(["make"])
    def InstallBinaries(self):
        self.SystemCommand(["sudo", "make", "install"])
        os.chdir("..")
            
class CMakeLibrarySourceInstallModule(SourceInstallModule):
    def __init__(self, downloadUrl, compiledFilePath, unpackedDirectory, postInstall = None, prereqs = None):
        self.postInstall = postInstall
        SourceInstallModule.__init__(self, downloadUrl, compiledFilePath, unpackedDirectory, prereqs)
    def Configure(self):
        configureDirectory = self.directory + "/build"
        self.SystemCommand(["mkdir", configureDirectory])
        os.chdir(configureDirectory)
    def Compile(self):
        self.SystemCommand(["cmake", "-DCMAKE_INSTALL_PREFIX=/usr/local", ".."])
    def InstallBinaries(self):
        self.SystemCommand(["sudo", "cmake", "--build", ".", "--target", "install"])
        if self.postInstall is not None:
            self.postInstall(self)
        os.chdir("../..")
            
class PackageManagerInstallModule(ApplicationInstallModule):
    def __init__(self, package, installByDefalt = False, configureCallback = None, prereqs = None, commandName = None):
        self.package = package
        self.commandName = package
        if commandName is not None:
            self.commandName = commandName
        ApplicationInstallModule.__init__(self, installByDefalt, configureCallback, prereqs)
    def IsInstalled(self):
        result = self.SystemCommand(["which", self.commandName])
        if(result == 0):
            print self.package + " is already installed."
            return True
            
        return False
    def Install(self):
        print "Installing " + self.package
        self.SystemCommand(["sudo", "apt-get", "install", "-y", self.package])
        print "Finished installing " + self.package

class Application:
    def __init__(self, displayName, installModule):
        self.displayName = displayName
        self.installModule = installModule

class Program:
    def MCryptPostInstall(self, installer):
        installer.SystemCommand(["sudo", "ln", "-s", "/etc/php5/conf.d/mcrypt.ini", "/etc/php5/mods-available/mcrypt.ini"])
        installer.SystemCommand(["sudo", "php5enmod", "mcrypt"])
    def LibRabbitMqPostInstall(self, installer):
        installer.SystemCommand(["sudo", "mv", "librabbitmq/librabbitmq.so", "/usr/lib/php5/20121212/librabbitmq.so"])
        installer.SystemCommand(["sudo", "mv", "librabbitmq/librabbitmq.so.1", "/usr/lib/php5/20121212/librabbitmq.so.1"])
        installer.SystemCommand(["sudo", "mv", "librabbitmq/librabbitmq.so.1.2.0", "/usr/lib/php5/20121212/librabbitmq.so.1.2.0"])
    
    def __init__(self):
        top = Tk()
        top.wm_title("Flying Monkeys")
        
        self.currentFrame = 0
        
        self.top = top
        
        php5devInstaller = PackageManagerInstallModule("php5-dev", True)
        librabbitmqInstaller = CMakeLibrarySourceInstallModule("https://github.com/alanxz/rabbitmq-c/archive/master.zip", "/usr/local/lib/librabbitmq.so", "rabbitmq-c-master", postInstall = self.LibRabbitMqPostInstall, prereqs = [PackageManagerInstallModule("cmake", True)])
        php5Installer = PackageManagerInstallModule("php5", True)
        php5jsonInstaller = PackageManagerInstallModule("php5-json", True)
        apacheInstaller = PackageManagerInstallModule("apache2", True)
        javajreInstaller = PackageManagerInstallModule("openjdk-7-jre", True)
        
        self.applications = {
            'Browsers': [
                Application("Chromium", PackageManagerInstallModule("chromium-browser", True)),
                Application("Firefox", PackageManagerInstallModule("firefox", True))
            ],
            'FTP Clients': [
                Application("gFTP", PackageManagerInstallModule("gftp", False)),
                Application("Filezilla", PackageManagerInstallModule("filezilla", True))
            ],
            'Source Control Clients': [
                Application("Git", PackageManagerInstallModule("git", True)),
                Application("Mercurial", PackageManagerInstallModule("mercurial", True, commandName = "hg")),
            ],
            'Servers': [
                Application("Apache", apacheInstaller)
            ],
            'Message Queues': [
                Application("RabbitMQ", PackageManagerInstallModule("rabbitmq-server", True, lambda x: x.SystemCommand(["sudo", "rabbitmq-plugins", "enable", "rabbitmq_management"])))
            ],
            'PHP': [
                Application("PHP", php5Installer),
                Application("PHP-amqp", PhpSourceInstallModule("http://pecl.php.net/get/amqp-1.0.10.tgz", "/usr/lib/php5/20121212/amqp.so", "amqp-1.0.10", configureOptions = { "with": "amqp" }, prereqs = [php5devInstaller, librabbitmqInstaller, php5Installer])),
                Application("Composer", BinaryInstallModule("https://getcomposer.org/download/1.0.0-alpha8/composer.phar", True, prereqs = [php5jsonInstaller])),
                Application("PHP5-Mcrypt", PackageManagerInstallModule("php5-mcrypt", True, self.MCryptPostInstall, prereqs = [apacheInstaller])),
                Application("Netbeans-PHP", DownloadInstallerModule("http://download.netbeans.org/netbeans/8.0/final/bundles/netbeans-8.0-php-linux.sh", "/usr/local/netbeans-8.0", True, prereqs = [javajreInstaller]))
            ],
            'Databases and Clients': [
                Application("MySQL Server", PackageManagerInstallModule("mysql-server", True)),
                Application("PHPMyAdmin", PackageManagerInstallModule("phpmyadmin", True)),
                Application("MySQL Workbench", PackageManagerInstallModule("mysql-workbench", True))
            ]
        }
        
        self.frames = []
        
        for key in self.applications.keys():
            self.frames.append(self.CreateFrame(key, self.applications[key]))
        
        self.totalFrames = len(self.frames)
        
        self.frames[0].backButton.pack_forget()
        self.frames[0].pack()
        
        self.commitButton = Button(top, text = "Commit", command = self.CommitApplications)
        
        self.SetFrameButtons()
        
        top.mainloop()
    
    def PreviousFrame(self):
        self.commitButton.pack_forget()
        self.HideAllFrames()
        
        self.currentFrame -= 1
        self.SetFrameButtons()
        self.frames[self.currentFrame].pack()
    
    def NextFrame(self):
        self.HideAllFrames()
        
        self.currentFrame += 1
        self.SetFrameButtons()
        self.frames[self.currentFrame].pack()
    
    def SetFrameButtons(self):
        if self.currentFrame == self.totalFrames - 1:
            self.frames[self.currentFrame].nextButton.pack_forget()
            self.commitButton.pack(side = BOTTOM)
            
        if self.currentFrame == 0:
            self.frames[self.currentFrame].backButton.pack_forget()
    
    def HideAllFrames(self):
        for frame in self.frames:
            frame.pack_forget()
    
    def CommitApplications(self):
        result = tkMessageBox.askquestion("Commit", "Are you sure? Clicking yes will install all checked applications.")
        if result == "yes":
            for key in self.applications.keys():
                for application in self.applications[key]:
                    application.installModule.Run()
        print "Done committing Applications"
    
    def CreateFrame(self, title, applications):
        frame = Frame(self.top)
        
        frameLabelTextVar = StringVar()
        frameLabelTextVar.set(title)
        frameLabel = Label(frame, textvariable = frameLabelTextVar)
        frameLabel.pack()
        
        for application in applications:
            chk = Checkbutton(frame, text = application.displayName, variable = application.installModule.installVar, width = 20)
            chk.pack()
        
        frame.backButton = Button(frame, text = "Back", command = self.PreviousFrame)
        frame.backButton.pack(side = LEFT)
        
        frame.nextButton = Button(frame, text = "Next", command = self.NextFrame)
        frame.nextButton.pack(side = RIGHT)
        
        return frame
        
if __name__ == "__main__":
    Program()
