import { Config, PluginConfig } from '../../framework/client/core/utils';


export class ReportsConfig extends PluginConfig {
  public static NAME = 'reports';
  public static VERSION = 'v1.0';
  public static API_URL = `${Config.API_URL}/plugins/${ReportsConfig.NAME}/${ReportsConfig.VERSION}`;
}
