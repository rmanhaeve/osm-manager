import data from './geofabrik.json';

export type GeofabrikEntry = {
  label: string;
  url: string;
  parent?: string;
  id: string;
};

export const GEOFABRIK_DATA = data as GeofabrikEntry[];
