const BANNER_LINE = /[═║╔╗╚╝─]/

export function isBannerLine(line: string): boolean {
  return BANNER_LINE.test(line)
}
