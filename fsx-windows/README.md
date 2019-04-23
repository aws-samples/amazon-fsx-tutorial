![](https://s3.amazonaws.com/aws-us-east-1/tutorial/AWS_logo_PMS_300x180.png)

![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_available.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_ingergration.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_ecryption-lock.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_fully-managed.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_lowcost-affordable.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_performance.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_scalable.png)![](https://s3.amazonaws.com/aws-us-east-1/tutorial/100x100_benefit_storage.png)


# **Amazon FSx for Windows File Server**

## Workshop

### Version 2019.04

fsx.w.wrkshp.2019.04

---

## Workshop Overview

### Overview

This will show solutions architects how to take advantage of a fully-managed Windows native file system for various application workloads like home directories, web serving & content management, enterprise applications, analytics, and media & entertainment.

This workshop will cover how to create FSx for Windows file systems and initiate an incremental file-system-consistent backup, as well as how to access the file system from Windows and Linux EC2 instances. We will also restore a backup as a new file system and setup Microsoft Distributed File System (DFS) Replication between two file systems across Availability Zones. For those of you who want to consolidate multiple file shares under a single namespace, we'll spend time setting up DFS Namespaces to consolidate multiple shares under a single namespace.

### Informational

You will be using your own AWS account for all workshop activities.
WARNING!! This workshop will exceed your free-usage tier. You will incur charges as a result of stepping through this workshop. Terminate all resources that were created during this workshop so you don’t continue to incur ongoing charges.

### The Workshop

Click on the links below to go to the FSx for Windows workshop.  These steps must be completed in order.


| Step | Workshop |
| :--- | :---
| 1 | [Create workshop environment](workshop/01-create-workshop-environment) |
| 2 | [Map a file share on Windows](workshop/02-map-file-share) |
| 3 | [Create new shares](workshop/03-create-new-shares)
| 4 | [Backup the file system](workshop/04-backup-file-system)
| 5 | [Mount a file system on Linux](workshop/05-mount-file-system)
| 6 | [Restore a backup](workshop/06-restore-backup)
| 7 | [Setup DFS](workshop/07-setup-dfs)


## License Summary

This sample code is made available under a modified MIT license. See the LICENSE file.
