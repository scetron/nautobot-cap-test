from nautobot.extras.jobs import *
from nautobot.dcim.models import Device, DeviceRole, Site
from nautobot.extras.models import Status

from git import Repo


class CapacityPlanning(Job):
    class Meta:
        name = "Capacity Planning"
        description = "Determine Percent Free physical ports by type from a subset of devices."

    site = ObjectVar(
        model = Site,
        display_field = 'name',
        description = 'Pick which site to run the report against.',
        label = 'Site',
        query_params = {'status': 'active'},
    )
    role = MultiObjectVar(
        model = DeviceRole,
        display_field = 'Device Role',
        description = 'Optionally, choose some roles to limit the devices in the report.',
        label = 'Roles',
        query_params = {'site': '$site', 'status': 'active'}
    )
    
    output = ""

    def run(self, data, commit):
        ACTIVE_STATUS = Status.objects.get(slug='active')
        self.log_debug(data['site'])
        devices = Device.objects.filter(site=data['site'], status=ACTIVE_STATUS)
        if devices:
            self.log_debug(devices.values_list('name', flat=True))
        else:
            self.log_failure(obj=data['site'], message=f'{data["site"].name} has no devices')
            return

        dict_output = {}
        table_output = [['Device', 'Port Type', 'Free Ports', 'Total Ports']]
        csv_output = ['device,int_type,free_tot,int_tot']
        for fdev in devices:
            dict_output.update({ fdev.name: {} })
            device_itypes = fdev.interfaces.filter(enabled=True,mgmt_only=False).values_list('type', flat=True).order_by('type').distinct()
            
            for itype in device_itypes:

                total_i = fdev.interfaces.filter(type=itype, enabled=True, mgmt_only=False).count()
                free_i = fdev.interfaces.filter(type=itype, mgmt_only=False, cable=None ).count()

                dict_output[fdev.name].update({ itype: {'total': total_i, 'free': free_i} })
                output = [
                    fdev.name, 
                    itype, 
                    str(free_i), 
                    str(total_i),
                ]
                table_output.append(output)
                csv_output.append(','.join(output))
            self.log_success(obj=fdev, message=f'Got interfaces for {fdev.name}')
        csv_output = '\n'.join(csv_output)
        
        self.log_success(table_output)
        
        return(csv_output)


    def post_run(self):
        # nothing to do if failed
        if self.failed:
            return

        self.log_debug(self.job_result)
        self.log_debug(self.results['output'])
        
